#!/usr/bin/env python3

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import math
from pathlib import Path
import statistics

from PIL import Image

from sim_dataset import FILENAME, SPLIT_LIGHTING, dataset_root, load_rooms, room_at


def validate(root, rooms, expected_rooms, check_loader, require_all_splits=False):
    with (root / 'metadata.csv').open(newline='') as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError('Metadata is empty')
    counts = Counter()
    positions = defaultdict(list)
    listed = set()
    images_by_split = defaultdict(set)
    for row in rows:
        relpath = Path(row['path'])
        if relpath.is_absolute() or len(relpath.parts) != 3 or '..' in relpath.parts or relpath in listed:
            raise ValueError(f'Invalid or repeated metadata path: {relpath}')
        listed.add(relpath)
        split, room, filename = relpath.parts
        fields = FILENAME.fullmatch(filename)
        if fields is None or room != row['room'] or row['lighting'] != SPLIT_LIGHTING.get(split):
            raise ValueError(f'Invalid filename, room, split or lighting: {relpath}')
        if any(row[key] != value for key, value in fields.groupdict().items()):
            raise ValueError(f'Filename and metadata coordinates differ: {relpath}')
        t, before, after = (int(row[key]) for key in ('timestamp_ns', 'pose_before_ns', 'pose_after_ns'))
        if not before <= t <= after or not 0 < after-before <= 30_000_000:
            raise ValueError(f'Invalid pose timestamps: {relpath}')
        x, y, yaw, distance = (float(row[key]) for key in ('x', 'y', 'yaw', 'distance_m'))
        if room_at(rooms, x, y) != room or not abs(yaw) <= math.pi + 1e-6 or not math.isfinite(distance):
            raise ValueError(f'Invalid ground truth: {relpath}')
        path = root / relpath
        with Image.open(path) as image:
            if image.format != 'PNG' or image.size != (512, 128) or image.mode != 'RGB':
                raise ValueError(f'Invalid PNG dimensions or color: {relpath}')
            image.load()
        if require_all_splits:
            images_by_split[split].add(hashlib.sha256(path.read_bytes()).digest())
        counts[split, room] += 1
        positions[split].append((t, distance))

    if require_all_splits:
        if set(positions) != set(SPLIT_LIGHTING):
            raise ValueError('All five dataset splits are required')
        reference = images_by_split['TrainingBaseline'] | images_by_split['Validation']
        if images_by_split['TrainingBaseline'] & images_by_split['Validation']:
            raise ValueError('An identical image occurs in train and validation')
        for name in ('TestCloudy', 'TestSunny', 'TestNight'):
            if reference & images_by_split[name]:
                raise ValueError(f'{name} contains an image identical to train or validation')
        print('No identical images shared across train/validation or references/test')
    for split, samples in positions.items():
        split_path = root / split
        actual_rooms = {path.name for path in split_path.iterdir() if path.is_dir()}
        actual_images = {path.relative_to(root) for path in split_path.rglob('*.png')}
        if actual_rooms != expected_rooms or actual_images != {path for path in listed if path.parts[0] == split}:
            raise ValueError(f'Folders or PNGs do not match metadata for {split}')
        if any(counts[split, room] == 0 for room in actual_rooms):
            raise ValueError(f'Empty room class in {split}')
        print(f'{split}: ' + ', '.join(f'{room}={counts[split,room]}' for room in sorted(actual_rooms)))
        samples.sort()
        if len(samples) >= 2:
            distances = [b[1]-a[1] for a,b in zip(samples, samples[1:])]
            if any(b[0] <= a[0] or b[1] <= a[1] for a,b in zip(samples, samples[1:])):
                raise ValueError(f'Timestamps or distances are not strictly increasing in {split}')
            print(f'Spacing (m) min/median/max: {min(distances):.3f}/{statistics.median(distances):.3f}/{max(distances):.3f}')
            if split in ('TrainingBaseline', 'Validation'):
                if not require_all_splits and any(abs(value - 0.20) > 0.075 for value in distances):
                    raise ValueError(f'An interval in {split} is beyond 0.20 ± 0.075 m')
                if require_all_splits:
                    on_grid = sum(abs(value - 0.20) <= 0.075 for value in distances)
                    if on_grid < 0.80 * len(distances):
                        raise ValueError(f'Too few ~0.20 m intervals in {split}: {on_grid}/{len(distances)}')
                    print(f'Intervals within 0.20 ± 0.075 m: {on_grid}/{len(distances)}')
        if check_loader:
            from torchvision.datasets import ImageFolder
            from torchvision.transforms import ToTensor
            dataset = ImageFolder(split_path, transform=ToTensor())
            if len(dataset) != len(samples) or dataset.classes != sorted(expected_rooms):
                raise ValueError(f'Unexpected ImageFolder results for {split}')
            for index, (path, _) in enumerate(dataset.samples):
                image, label = dataset[index]
                x0, y0, a0 = (path.index(token) for token in ('_x', '_y', '_a'))
                coordinates = (float(path[x0+2:y0]), float(path[y0+2:a0]))
                if tuple(image.shape) != (3,128,512) or room_at(rooms, *coordinates) != dataset.classes[label]:
                    raise ValueError(f'Legacy coordinate parsing or ImageFolder check failed: {path}')
            print(f'ImageFolder and legacy coordinate parsing OK: {dataset.class_to_idx}')


def main():
    parser = argparse.ArgumentParser(description='Validate panoramas and Gazebo metadata')
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--rooms', type=Path, default=Path('map/rooms.yaml'))
    parser.add_argument('--expected-rooms', nargs='+')
    parser.add_argument('--imagefolder', action='store_true')
    parser.add_argument('--full', action='store_true', help='Require all five splits and check exact duplicates')
    args = parser.parse_args()
    rooms = load_rooms(args.rooms)
    expected = set(args.expected_rooms or rooms)
    if not expected <= rooms.keys():
        parser.error('Unknown room label')
    validate(dataset_root(args.dataset), rooms, expected, args.imagefolder, args.full)


if __name__ == '__main__':
    main()
