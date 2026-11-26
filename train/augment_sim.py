"""Build deterministic augmentation folders from the original cloudy training set."""
import argparse
import csv
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image


VARIANTS = {
    'DA1': (160, 145, 130, 115, 100),
    'DA2': (-160, -145, -130, -115, -100),
    'DA3': (0.15, 0.30, 0.45, -0.15, -0.30, -0.45),
    'DA4': (0.5, 0.75, 1.25, 1.5, 1.75),
    'DA5': (0.25, 0.5, 0.75, 1.25, 1.5),
    'DA6': tuple(range(10, 360, 10)),
}


def encode(array):
    return Image.fromarray(np.clip(np.rint(array), 0, 255).astype(np.uint8))


def apply(image, variant, value, rng):
    rgb = np.asarray(image)
    if variant == 'DA6':
        return Image.fromarray(np.roll(rgb, round(image.width * value / 360), axis=1))
    if variant == 'DA5':
        hsv = np.array(image.convert('HSV'))
        hsv[..., 1] = np.clip(np.rint(hsv[..., 1].astype(np.float32) * value), 0, 255)
        return Image.frombytes('HSV', image.size, hsv.tobytes()).convert('RGB')
    rgb = rgb.astype(np.float32)
    if variant == 'DA4':
        return encode(64 + value * (rgb - 64))
    if variant == 'DA3':
        return encode(rgb + value * (255 - rgb) if value > 0 else rgb * (1 + value))
    height, width = rgb.shape[:2]
    y, x = np.ogrid[:height, :width]
    weights = np.zeros((height, width), dtype=np.float32)
    for _ in range(2):
        cx, cy = rng.integers([0, 0], [width, height])
        radius = rng.integers(15, 41) / 2
        dx = np.abs(x - cx)
        dx = np.minimum(dx, width - dx)
        weights = np.maximum(weights, np.clip(1 - (dx**2 + (y-cy)**2) / radius**2, 0, 1))
    return encode(rgb + value * weights[..., None])


def generate(root, output, variant, seed):
    baseline = root / 'TrainingBaseline'
    images = sorted(baseline.glob('*/*.png'))
    if not images:
        raise ValueError(f'No training images in {baseline}')
    with (root / 'metadata.csv').open(newline='') as file:
        coordinates = {row['path']: row for row in csv.DictReader(file)}
    output.mkdir(parents=True, exist_ok=True)
    destination = output / variant
    manifest = output / f'{variant}.csv'
    if destination.exists() or manifest.exists():
        raise FileExistsError(f'{variant} already exists in {output}')
    with TemporaryDirectory(prefix='.augment-', dir=output) as temporary:
        stage = Path(temporary)
        folder = stage / variant
        with (stage / 'manifest.csv').open('w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(('path', 'source', 'variant', 'parameter', 'timestamp_ns', 'x', 'y', 'yaw'))
            for index, source in enumerate(images):
                origin = source.relative_to(root).as_posix()
                pose = coordinates[origin]
                room = source.parent.name
                (folder / room).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, folder / room / source.name)
                writer.writerow((f'{variant}/{room}/{source.name}', origin, variant, 'original',
                                 pose['timestamp_ns'], pose['x'], pose['y'], pose['yaw']))
                with Image.open(source) as opened:
                    image = opened.convert('RGB')
                prefix, coordinate_suffix = source.stem.split('_x', maxsplit=1)
                for number, value in enumerate(VARIANTS[variant], 1):
                    rng = np.random.default_rng([seed, int(variant[2:]), index, number])
                    yaw = float(pose['yaw'])
                    if variant == 'DA6':
                        yaw = math.remainder(yaw + math.radians(value), 2 * math.pi)
                    coord = coordinate_suffix.rsplit('_a', maxsplit=1)[0]
                    name = f'{prefix}-v{number:02}_x{coord}_a{yaw:.6f}.png'
                    apply(image, variant, value, rng).save(folder / room / name, compress_level=2)
                    writer.writerow((f'{variant}/{room}/{name}', origin, variant, value,
                                     pose['timestamp_ns'], pose['x'], pose['y'], f'{yaw:.6f}'))
        folder.rename(destination)
        (stage / 'manifest.csv').rename(manifest)
    print(f'{variant}: {len(images) * (len(VARIANTS[variant]) + 1)} images', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=Path('data/sim-seven-office'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--variants', nargs='+', choices=VARIANTS)
    args = parser.parse_args()
    for variant in args.variants or VARIANTS:
        generate(args.dataset, args.output or args.dataset / 'TrainingDA', variant, args.seed)


if __name__ == '__main__':
    main()
