#!/usr/bin/env python3

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
from uuid import uuid4

import yaml

from sim_dataset import SPLIT_LIGHTING, dataset_root


RUN_WORLDS = {
    'training': SPLIT_LIGHTING['TrainingBaseline'],
    'TestCloudy': SPLIT_LIGHTING['TestCloudy'],
    'TestSunny': SPLIT_LIGHTING['TestSunny'],
    'TestNight': SPLIT_LIGHTING['TestNight'],
}


def capture(args, case, points):
    x, y = points[0]
    yaw = math.atan2(points[1][1]-y, points[1][0]-x)
    world = RUN_WORLDS[case]
    run = args.output / case
    if run.exists():
        if (run / 'complete').is_file():
            print(f'Reusing completed run {run}', flush=True)
            return
        raise FileExistsError(f'Existing incomplete run: {run}. Choose another staging directory or archive it.')
    env = os.environ.copy()
    env.update(IGN_PARTITION=f'house_capture_{uuid4().hex[:12]}',
               ROS_DOMAIN_ID=str(args.domain), ROS_LOCALHOST_ONLY='1')
    print(f'{case} on {world}: {len(points)} waypoints', flush=True)
    launch_command = [
        'ros2', 'launch', 'house_localization_sim', 'house.launch.py',
        f'world:={world}', 'panorama:=true', 'collection:=true',
        f'real_time_factor:={args.real_time_factor}', f'x:={x}', f'y:={y}', f'yaw:={yaw}',
    ]
    with (args.output / f'{case}.log').open('w') as log:
        launch = subprocess.Popen(launch_command, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            subprocess.run([
                'ros2', 'run', 'house_localization_sim', 'collect_pilot.py',
                '--run', case, '--waypoints', str(args.routes), '--output', str(run),
                '--timeout', str(args.timeout),
            ], check=True, env=env, timeout=args.timeout + 20)
            if launch.poll() is not None:
                raise RuntimeError(f'Unexpected Gazebo exit during {case}')
        finally:
            if launch.poll() is None:
                launch.send_signal(signal.SIGINT)
                launch.wait(timeout=20)
    (run / 'run.json').write_text(json.dumps({
        'world': world, 'waypoints': points, 'requested_real_time_factor': args.real_time_factor,
    }, indent=2) + '\n')
    (run / 'complete').touch()


def main():
    parser = argparse.ArgumentParser(description='Capture independent Gazebo routes sequentially')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--routes', type=Path, default=Path('simulation/house_localization_sim/config/routes.yaml'))
    parser.add_argument('--run', choices=RUN_WORLDS, action='append')
    parser.add_argument('--domain', type=int, default=145)
    parser.add_argument('--real-time-factor', type=float, default=3.0)
    parser.add_argument('--timeout', type=float, default=900)
    args = parser.parse_args()
    args.output = dataset_root(args.output)
    args.output.mkdir(parents=True, exist_ok=True)
    routes = yaml.safe_load(args.routes.read_text())
    for case in args.run or RUN_WORLDS:
        capture(args, case, routes['training' if case == 'training' else 'testing'])


if __name__ == '__main__':
    main()
