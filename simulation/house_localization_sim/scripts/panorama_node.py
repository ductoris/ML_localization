#!/usr/bin/env python3

import cv2
from cv_bridge import CvBridge
from message_filters import Subscriber, TimeSynchronizer
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


DIRECTIONS = ("front", "left", "back", "right")
WIDTH = 512
HEIGHT = 128


def build_remap(source_width, source_height, horizontal_fov_deg, elevation_top_deg,
                elevation_bottom_deg, front_column, azimuth_sign, blend_half_width_deg):
    if source_width < 2 or source_height < 2 or 4 * source_width >= 32767:
        raise ValueError("Invalid pinhole image dimensions for OpenCV remap")
    if not 90 < horizontal_fov_deg < 180:
        raise ValueError("Pinhole horizontal field of view must be between 90 and 180 degrees")
    if not -90 < elevation_bottom_deg < elevation_top_deg < 90:
        raise ValueError("Elevation bounds must be ordered and within (-90, 90) degrees")
    if not 0 <= front_column < WIDTH or azimuth_sign not in (-1, 1):
        raise ValueError("Invalid front column or azimuth sign")
    if not 0 < blend_half_width_deg < 45:
        raise ValueError("Blend half-width must be between 0 and 45 degrees")

    azimuth = azimuth_sign * (np.arange(WIDTH) - front_column) * (2 * np.pi / WIDTH)
    elevations = np.deg2rad(np.linspace(elevation_top_deg, elevation_bottom_deg, HEIGHT))
    relative = azimuth - np.arange(len(DIRECTIONS))[:, None] * (np.pi / 2)
    off_axis = np.arccos(np.clip(np.cos(relative), -1, 1))
    primary, secondary = np.argsort(off_axis, axis=0)[:2]
    columns = np.arange(WIDTH)
    focal = source_width / (2 * np.tan(np.deg2rad(horizontal_fov_deg) / 2))
    angle_gap = off_axis[secondary, columns] - off_axis[primary, columns]
    blend = np.clip(angle_gap / (2 * np.deg2rad(blend_half_width_deg)), 0, 1)
    secondary_weight = (0.25 * (1 + np.cos(np.pi * blend))).astype(np.float32)[None, :, None]
    # Outside a blend band both remaps can use the primary camera.
    secondary = np.where(blend < 1, secondary, primary)

    def project(camera_index):
        delta = relative[camera_index, columns]
        # Gazebo cameras look along +X. +Y is left and +Z is up in the rig frame.
        source_x = (source_width - 1) / 2 - focal * np.tan(delta)
        source_y = (source_height - 1) / 2 - focal * np.tan(elevations[:, None]) / np.cos(delta)
        if np.any((source_x < 0) | (source_x >= source_width - 1)) or np.any(
            (source_y < 0) | (source_y >= source_height - 1)
        ):
            raise ValueError("Pinhole coverage is insufficient. Adjust elevation bounds or the blend width.")
        mosaic_x = np.broadcast_to(source_x + camera_index * source_width, (HEIGHT, WIDTH))
        return mosaic_x.astype(np.float32), source_y.astype(np.float32)

    return project(primary), project(secondary), secondary_weight


class PanoramaNode(Node):
    def __init__(self):
        super().__init__("panorama")
        defaults = {
            "source_width": 320,
            "source_height": 320,
            "horizontal_fov_deg": 110.0,
            "elevation_top_deg": 19.0,
            "elevation_bottom_deg": -41.0,
            "front_column": 128.0,
            "azimuth_sign": -1,
            "blend_half_width_deg": 3.0,
        }
        params = {name: self.declare_parameter(name, value).value for name, value in defaults.items()}
        self.source_shape = (params["source_height"], params["source_width"], 3)
        self.primary_map, self.secondary_map, self.secondary_weight = build_remap(**params)
        self.bridge = CvBridge()
        self.output = self.create_publisher(Image, "/panorama/image_raw", qos_profile_sensor_data)
        self.images = [
            Subscriber(self, Image, f"/panorama/source/{direction}", qos_profile=qos_profile_sensor_data)
            for direction in DIRECTIONS
        ]
        self.sync = TimeSynchronizer(self.images, queue_size=8)
        self.sync.registerCallback(self.stitch)

    def stitch(self, *messages):
        frames = [self.bridge.imgmsg_to_cv2(message, desired_encoding="rgb8") for message in messages]
        if any(frame.shape != self.source_shape for frame in frames):
            self.get_logger().error("Pinhole image dimensions differ from camera.yaml", throttle_duration_sec=5)
            return
        strip = np.concatenate(frames, axis=1)
        primary = cv2.remap(strip, *self.primary_map, interpolation=cv2.INTER_LINEAR)
        secondary = cv2.remap(strip, *self.secondary_map, interpolation=cv2.INTER_LINEAR)
        panorama = np.rint(primary + (secondary.astype(np.float32) - primary) * self.secondary_weight).astype(np.uint8)
        image = self.bridge.cv2_to_imgmsg(panorama, encoding="rgb8")
        image.header.stamp = messages[0].header.stamp
        image.header.frame_id = "panorama_frame"
        self.output.publish(image)


def main():
    rclpy.init()
    node = None
    try:
        node = PanoramaNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
