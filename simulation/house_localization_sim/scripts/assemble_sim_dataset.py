#!/usr/bin/env python3

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from check_sim_dataset import validate
from sim_dataset import FIELDS, SPLIT_LIGHTING, dataset_root, load_rooms


RUNS = {
    'training': ('TrainingBaseline', 'Validation'),
    'TestCloudy': ('TestCloudy',),
    'TestSunny': ('TestSunny',),
    'TestNight': ('TestNight',),
}
POSITION_LIMIT_M = 0.075
YAW_LIMIT_RAD = 0.15


def load_run(root, expected_splits):
    if not (root / 'complete').is_file():
        raise ValueError(f'Run is incomplete: {root}')
    with (root / 'metadata.csv').open(newline='') as file:
        rows = list(csv.DictReader(file))
    if {Path(row['path']).parts[0] for row in rows} != set(expected_splits):
        raise ValueError(f'Unexpected splits in {root}')
    manifest = json.loads((root / 'run.json').read_text())
    if manifest['world'] != SPLIT_LIGHTING[expected_splits[0]] or len(manifest['waypoints']) < 2:
        raise ValueError(f'Unexpected world or route in {root}')
    return rows, manifest


def near_reference(row, references):
    x, y, yaw = (float(row[key]) for key in ('x', 'y', 'yaw'))
    return any(math.hypot(x-ref_x, y-ref_y) < POSITION_LIMIT_M
               and abs(math.remainder(yaw-ref_yaw, 2*math.pi)) < YAW_LIMIT_RAD
               for ref_x, ref_y, ref_yaw in references[row['room']])


def assemble(source, output, rooms, min_images):
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    references = defaultdict(list)
    reference_hashes = set()
    counts = {name: Counter() for name in SPLIT_LIGHTING}
    discarded = {name: Counter() for name in SPLIT_LIGHTING}
    manifests = {}
    with TemporaryDirectory(prefix='.sim-assemble-', dir=output.parent) as temp:
        destination = Path(temp) / 'dataset'
        destination.mkdir()
        with (destination / 'metadata.csv').open('x', newline='') as file:
            writer = csv.DictWriter(file, FIELDS)
            writer.writeheader()
            for case, splits in RUNS.items():
                root = source / case
                rows, manifests[case] = load_run(root, splits)
                for row in rows:
                    relative = Path(row['path'])
                    if relative.is_absolute() or len(relative.parts) != 3 or '..' in relative.parts:
                        raise ValueError(f'Invalid relative image path: {relative}')
                    split, room, _ = relative.parts
                    frame = root / relative
                    if not frame.resolve().is_relative_to(root.resolve()):
                        raise ValueError(f'Image escapes the run directory: {frame}')
                    digest = hashlib.sha256(frame.read_bytes()).digest()
                    if case == 'training':
                        if digest in reference_hashes:
                            discarded[split]['identical_reference_image'] += 1
                            continue
                        reference_hashes.add(digest)
                        references[room].append(tuple(float(row[key]) for key in ('x', 'y', 'yaw')))
                    elif digest in reference_hashes or near_reference(row, references):
                        discarded[split]['near_or_identical_to_reference'] += 1
                        continue
                    target = destination / relative
                    if target.exists():
                        raise ValueError(f'Duplicate relative image path: {relative}')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(frame, target)
                    writer.writerow(row)
                    counts[split][room] += 1
        test_route = manifests['TestCloudy']['waypoints']
        if manifests['training']['waypoints'] == test_route or any(
            manifests[case]['waypoints'] != test_route for case in ('TestSunny', 'TestNight')
        ):
            raise ValueError('Expected separate training and test routes, with identical waypoints across test runs')
        for split, tally in counts.items():
            missing = [room for room in sorted(rooms) if tally[room] < min_images]
            if missing:
                raise ValueError(f'{split}: fewer than {min_images} images in {missing}')
        validate(destination, rooms, set(rooms), False, require_all_splits=True)
        report = {'images_by_split_and_room': counts, 'discarded': discarded, 'runs': manifests,
                  'pose_exclusion_radius_m': POSITION_LIMIT_M, 'pose_exclusion_yaw_rad': YAW_LIMIT_RAD}
        (destination / 'collection-report.json').write_text(json.dumps(report, indent=2) + '\n')
        destination.rename(output)
    print(f'Validated dataset: {output}/')


def main():
    parser = argparse.ArgumentParser(description='Assemble and validate four completed Gazebo runs')
    parser.add_argument('runs', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--rooms', type=Path, default=Path('map/rooms.yaml'))
    parser.add_argument('--min-images', type=int, default=6)
    args = parser.parse_args()
    if args.min_images < 1:
        parser.error('--min-images must be positive')
    assemble(dataset_root(args.runs), dataset_root(args.output), load_rooms(args.rooms), args.min_images)


if __name__ == '__main__':
    main()
