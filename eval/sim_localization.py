"""Two-stage visual localization for a labeled reference set."""
import csv
import math
from pathlib import Path
import statistics
import time
import torch
from torchvision.datasets import ImageFolder
from torchvision.transforms import ToTensor


TEST_SPLITS = ('TestCloudy', 'TestSunny', 'TestNight')


class LandscapeDataset(ImageFolder):
    """Read RGB panoramas and attach actual capture coordinates from metadata."""

    def __init__(self, root, split, coordinates, classes, transform=None):
        super().__init__(root / split, transform=transform or ToTensor())
        self.split = split
        self.root = root
        if self.classes != list(classes):
            raise ValueError(f'{split}: expected classes {classes}, found {self.classes}')
        self.relative_paths = [Path(path).relative_to(root).as_posix() for path, _ in self.samples]
        self.coordinates = [coordinates[path] for path in self.relative_paths] if coordinates else []

    def __getitem__(self, index):
        image, label = super().__getitem__(index)
        if image.shape != (3, 128, 512):
            raise ValueError(f'Expected an RGB 512×128 image: {self.samples[index][0]}')
        return image, label


class HierarchicalLocalizer:
    def __init__(self, model, device, batch_size, reference_set):
        self.model = model.eval()
        self.device = device
        self.features = None
        self.hook = model.avgpool.register_forward_hook(self._capture)
        buckets = {label: [] for label in range(len(reference_set.classes))}
        coordinates = {label: [] for label in buckets}
        loader = torch.utils.data.DataLoader(reference_set, batch_size=batch_size)
        row = 0
        with torch.inference_mode():
            for images, labels in loader:
                self.model(self.to_device(images))
                for descriptor, label in zip(self.features, labels.tolist()):
                    buckets[label].append(descriptor)
                    coordinates[label].append(reference_set.coordinates[row])
                    row += 1
        self.references = {label: torch.stack(rows) for label, rows in buckets.items()}
        self.positions = coordinates

    def _capture(self, _layer, _inputs, output):
        self.features = output.flatten(1)

    def to_device(self, batch):
        return batch.to(self.device, memory_format=torch.channels_last)

    @torch.inference_mode()
    def predict(self, image):
        logits = self.model(image)
        room = int(logits.argmax(1).item())
        pairwise_distance_squared = (self.references[room] - self.features[0]).square().sum(1)
        index = int(pairwise_distance_squared.argmin().item())
        return room, self.positions[room][index]

    def close(self):
        self.hook.remove()


def read_positions(root):
    with (root / 'metadata.csv').open(newline='') as file:
        rows = list(csv.DictReader(file))
    result = {entry['path']: (float(entry['x']), float(entry['y'])) for entry in rows}
    if len(result) != len(rows) or any(not all(math.isfinite(value) for value in xy) for xy in result.values()):
        raise ValueError('Metadata contains duplicate paths or nonfinite coordinates')
    return result


def evaluate(localizer, dataset, csv_writer):
    errors, timings = [], []
    confusion = [[0] * len(dataset.classes) for _ in dataset.classes]
    gpu = localizer.device.type == 'cuda'
    first, _ = dataset[0]
    warmup = localizer.to_device(first.unsqueeze(0))
    for _ in range(12):
        localizer.predict(warmup)
    for index, frame in enumerate(dataset.relative_paths):
        image, room_gt = dataset[index]
        batch = localizer.to_device(image.unsqueeze(0))
        if gpu:
            torch.cuda.synchronize(localizer.device)
        start = time.perf_counter_ns()
        room_pred, (x_est, y_est) = localizer.predict(batch)
        elapsed_ms = (time.perf_counter_ns() - start) / 1e6
        x_gt, y_gt = dataset.coordinates[index]
        error = math.hypot(x_est - x_gt, y_est - y_gt)
        errors.append(error)
        timings.append(elapsed_ms)
        confusion[room_gt][room_pred] += 1
        csv_writer.writerow((dataset.split, frame, dataset.classes[room_gt], dataset.classes[room_pred],
                             x_gt, y_gt, x_est, y_est, error, elapsed_ms))
    hits = sum(confusion[i][i] for i in range(len(confusion)))
    return {
        'n': len(errors), 'room_accuracy': hits / len(errors),
        'mae_m': statistics.mean(errors), 'variance_m2': statistics.pvariance(errors),
        'rmse_m': math.sqrt(statistics.mean(value * value for value in errors)),
        'inference_ms': statistics.mean(timings), 'confusion': confusion,
    }
