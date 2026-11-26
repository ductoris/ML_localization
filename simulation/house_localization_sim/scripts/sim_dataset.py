from pathlib import Path
import re

import yaml


FILENAME = re.compile(r't(?P<timestamp_ns>[0-9]+)_x(?P<x>-?[0-9]+\.[0-9]+)_y(?P<y>-?[0-9]+\.[0-9]+)_a(?P<yaw>-?[0-9]+\.[0-9]+)\.png')
FIELDS = ('path', 'timestamp_ns', 'x', 'y', 'yaw', 'room', 'lighting',
          'pose_before_ns', 'pose_after_ns', 'distance_m')
SPLIT_LIGHTING = {
    'TrainingBaseline': 'cloudy', 'Validation': 'cloudy', 'TestCloudy': 'cloudy',
    'TestNight': 'night', 'TestSunny': 'sunny',
}


def dataset_root(path):
    root = Path(path).expanduser().resolve()
    if any(marker in str(root) for marker in ('_x', '_y', '_a')):
        raise ValueError("Dataset path contains a reserved coordinate marker: _x, _y or _a")
    return root


def load_rooms(path):
    with Path(path).open() as file:
        return yaml.safe_load(file)


def room_at(rooms, x, y, margin=0.15):
    names = [
        name for name, box in rooms.items()
        if box['xmin'] + margin < x < box['xmax'] - margin
        and box['ymin'] + margin < y < box['ymax'] - margin
    ]
    return names[0] if len(names) == 1 else None
