#!/usr/bin/env python3

import argparse
from collections import deque
import csv
from dataclasses import dataclass
import math
from pathlib import Path
import sys
import time

import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped, Twist
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
import yaml

from sim_dataset import FIELDS, SPLIT_LIGHTING, dataset_root, load_rooms, room_at


@dataclass
class Pose:
    stamp: int
    x: float
    y: float
    yaw: float
    distance: float = 0.0


def stamp(message):
    value = message.header.stamp
    return value.sec * 1_000_000_000 + value.nanosec


def wrapped(angle):
    return math.remainder(angle, 2 * math.pi)


class RouteCollector(Node):
    def __init__(self, root, rooms, waypoints, run):
        super().__init__('route_collector')
        self.run = run
        self.station = 0
        self.last_frame = None
        self.progress = None
        self.last_command = None
        self.root = root
        self.rooms = rooms
        self.waypoints = deque(waypoints[1:])
        self.start = waypoints[0]
        self.poses = deque(maxlen=256)
        self.images = deque(maxlen=20)
        self.initial_distance = None
        self.count = 0
        self.done = False
        self.failure = None
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Twist, '/diffdrive_controller/cmd_vel_unstamped', 10)
        self.create_subscription(PoseStamped, '/ground_truth/pose', self.receive_pose, qos_profile_sensor_data)
        self.create_subscription(Image, '/panorama/image_raw', self.receive_image, qos_profile_sensor_data)
        self.csv_file = (root / 'metadata.csv').open('x', newline='')
        self.writer = csv.DictWriter(self.csv_file, FIELDS)
        self.writer.writeheader()
        self.csv_file.flush()

    def receive_image(self, message):
        if self.done or (self.images and stamp(message) <= stamp(self.images[-1])):
            return
        self.images.append(message)

    def receive_pose(self, message):
        if self.done or message.header.frame_id != 'house':
            return
        position, q = message.pose.position, message.pose.orientation
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1-2*(q.y*q.y + q.z*q.z))
        point = Pose(stamp(message), position.x, position.y, yaw)
        if self.poses:
            prior = self.poses[-1]
            if point.stamp <= prior.stamp:
                if point.stamp < prior.stamp:
                    self.failure = 'Gazebo simulation time moved backwards'
                    self.done = True
                return
            step = math.hypot(point.x - prior.x, point.y - prior.y)
            if step > 0.20:
                self.failure = 'Unexpected ground-truth pose jump'
                self.done = True
                return
            point.distance = prior.distance + step
        self.poses.append(point)

    def save_ready_frames(self):
        if len(self.poses) < 2:
            return
        while self.images and stamp(self.images[0]) <= self.poses[-1].stamp:
            image = self.images.popleft()
            t = stamp(image)
            for before, after in zip(self.poses, list(self.poses)[1:]):
                if before.stamp <= t <= after.stamp:
                    break
            else:
                continue
            interval = after.stamp - before.stamp
            if interval > 30_000_000:
                continue
            f = (t - before.stamp) / interval
            x = before.x + f * (after.x - before.x)
            y = before.y + f * (after.y - before.y)
            yaw = wrapped(before.yaw + f * wrapped(after.yaw - before.yaw))
            distance = before.distance + f * (after.distance - before.distance)
            if self.initial_distance is None:
                self.initial_distance = distance
            along = distance - self.initial_distance
            room = room_at(self.rooms, x, y)
            split = self.run
            if self.run in ('pilot', 'training'):
                step = 0.20 if self.run == 'pilot' else 0.10
                if along + 1e-8 < self.station * step:
                    continue
                station = int((along + 1e-8) / step)
                self.station = station + 1
                split = 'Validation' if self.run == 'training' and station % 2 else 'TrainingBaseline'
            elif self.last_frame is not None and math.hypot(x-self.last_frame[0], y-self.last_frame[1]) < 0.012:
                continue
            if room is None or (self.run == 'pilot' and room != 'hallway'):
                continue
            if (image.width, image.height, image.encoding) != (512, 128, 'rgb8'):
                raise ValueError('Panorama must be 512 x 128 RGB8')
            relpath = f'{split}/{room}/t{t}_x{x:.6f}_y{y:.6f}_a{yaw:.6f}.png'
            destination = self.root / relpath
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.with_suffix('.partial.png')
            if not cv2.imwrite(str(temp), self.bridge.imgmsg_to_cv2(image, 'bgr8')):
                raise OSError(f'Could not write {temp}')
            temp.rename(destination)
            self.writer.writerow(dict(path=relpath, timestamp_ns=t, x=f'{x:.6f}', y=f'{y:.6f}',
                                      yaw=f'{yaw:.6f}', room=room, lighting=SPLIT_LIGHTING[split],
                                      pose_before_ns=before.stamp, pose_after_ns=after.stamp,
                                      distance_m=f'{along:.6f}'))
            self.csv_file.flush()
            self.last_frame = (x, y)
            self.count += 1

    def drive(self):
        if not self.poses or self.done:
            return
        pose = self.poses[-1]
        if self.run == 'pilot' and room_at(self.rooms, pose.x, pose.y) != 'hallway':
            raise ValueError('Robot left the pilot hallway')
        if self.last_command is None:
            if math.hypot(pose.x-self.start[0], pose.y-self.start[1]) > 0.20:
                raise ValueError('Spawn robot at the first waypoint before starting the pilot')
        self.save_ready_frames()
        if self.initial_distance is None or self.publisher.get_subscription_count() == 0:
            return
        if self.last_command is not None and pose.stamp - self.last_command < 45_000_000:
            return
        self.last_command = pose.stamp
        x, y = self.waypoints[0]
        distance = math.hypot(x-pose.x, y-pose.y)
        if self.progress is None or distance < self.progress[0] - 0.05:
            self.progress = (distance, pose.stamp)
        elif pose.stamp - self.progress[1] > 12_000_000_000:
            raise RuntimeError(f'No progress toward {(x, y)} from {(pose.x, pose.y, pose.yaw)}')
        if distance < 0.070:
            print(f'Waypoint {(x, y)} reached, {len(self.waypoints)-1} remaining ({self.count} frames)', flush=True)
            self.waypoints.popleft()
            self.progress = None
            self.done = not self.waypoints
            self.publisher.publish(Twist())
            return
        heading = wrapped(math.atan2(y-pose.y, x-pose.x) - pose.yaw)
        command = Twist()
        command.angular.z = max(-1.25, min(1.25, 3.0*heading))
        if abs(heading) < 0.25:
            command.linear.x = min(0.29, max(0.10, 1.8*distance))
        self.publisher.publish(command)


def main():
    parser = argparse.ArgumentParser(description='Collect Gazebo panoramas by following a waypoint route')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rooms', type=Path, default=Path('map/rooms.yaml'))
    parser.add_argument('--waypoints', type=Path)
    parser.add_argument('--run', choices=('pilot', 'training', 'TestCloudy', 'TestSunny', 'TestNight'), default='pilot')
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    root = dataset_root(args.output)
    rooms = load_rooms(args.rooms)
    config_name = 'hallway_pilot.yaml' if args.run == 'pilot' else 'routes.yaml'
    route_file = args.waypoints or Path('simulation/house_localization_sim/config') / config_name
    with route_file.open() as file:
        key = 'waypoints' if args.run == 'pilot' else 'training' if args.run == 'training' else 'testing'
        waypoints = yaml.safe_load(file)[key]
    if len(waypoints) < 2 or (args.run == 'pilot' and any(room_at(rooms, *point) != 'hallway' for point in waypoints)):
        parser.error('A route needs two or more valid waypoints')
    root.mkdir(parents=True, exist_ok=False)
    rclpy.init(args=[sys.argv[0]])
    pilot = RouteCollector(root, rooms, waypoints, args.run)
    try:
        deadline = time.monotonic() + args.timeout
        while rclpy.ok() and not pilot.done and time.monotonic() < deadline:
            rclpy.spin_once(pilot, timeout_sec=0.03)
            pilot.drive()
        if not pilot.done or pilot.failure or pilot.count < 2:
            raise RuntimeError(pilot.failure or f'Route stopped before completion ({pilot.count} frames)')
        print(f'{pilot.count} frames written to {root}')
    finally:
        if rclpy.ok():
            pilot.publisher.publish(Twist())
        pilot.csv_file.close()
        pilot.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
