#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import Image


def main():
    parser = argparse.ArgumentParser(description="Save one frame from /panorama/image_raw")
    parser.add_argument("output", type=Path, help="PNG output path")
    parser.add_argument("--timeout", type=float, default=30.0, help="Maximum wait in wall-clock seconds")
    args = parser.parse_args(remove_ros_args(args=sys.argv)[1:])
    if args.output.suffix.lower() != ".png" or args.timeout <= 0:
        parser.error("Specify a .png file and a positive timeout")

    rclpy.init(args=sys.argv)
    node = rclpy.create_node("save_panorama")
    samples = []
    node.create_subscription(Image, "/panorama/image_raw", samples.append, qos_profile_sensor_data)
    try:
        deadline = time.monotonic() + args.timeout
        while not samples and rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.25)
        if not samples:
            print("No panorama received before timeout", file=sys.stderr)
            return 1
        frame = samples[0]
        if (frame.width, frame.height, frame.encoding) != (512, 128, "rgb8"):
            print("Expected a 512 × 128 RGB panorama", file=sys.stderr)
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        bgr = CvBridge().imgmsg_to_cv2(frame, desired_encoding="bgr8")
        if not cv2.imwrite(str(args.output), bgr):
            print(f"Could not write {args.output}", file=sys.stderr)
            return 1
        print(args.output)
        return 0
    except KeyboardInterrupt:
        return 130
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
