"""Train and evaluate a simulation checkpoint without importing the COLD settings."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import torch
from torch import nn
from torchvision import models
from torchvision.transforms import PILToTensor
import yaml

from eval.sim_localization import (
    HierarchicalLocalizer, LandscapeDataset, TEST_SPLITS, evaluate, read_positions,
)


BACKBONES = {
    'mobilenet_v3_large': (models.mobilenet_v3_large, models.MobileNet_V3_Large_Weights.IMAGENET1K_V1, 3),
    'alexnet': (models.alexnet, models.AlexNet_Weights.IMAGENET1K_V1, 6),
    'convnext_large': (models.convnext_large, models.ConvNeXt_Large_Weights.IMAGENET1K_V1, 2),
}
VARIANTS = ('noDA', 'DA1', 'DA2', 'DA3', 'DA4', 'DA5', 'DA6')


def seed_everything(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build(name, classes, pretrained):
    factory, weights, index = BACKBONES[name]
    model = factory(weights=weights if pretrained else None)
    model.classifier[index] = nn.Linear(model.classifier[index].in_features, classes)
    return model


def atomic_save(value, path):
    tmp = path.with_suffix('.partial')
    torch.save(value, tmp)
    tmp.replace(path)


def save_json(value, path):
    tmp = path.with_suffix('.partial')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


class CachedBatches:
    """Decode once into byte tensors, then convert each batch as ToTensor does."""

    def __init__(self, dataset, device, batch_size, workers, rng):
        self.dataset = dataset
        self.batch_size = batch_size
        self.rng = rng
        self.images = torch.empty((len(dataset), 3, 128, 512), dtype=torch.uint8,
                                  device=device, memory_format=torch.channels_last)
        self.labels = torch.tensor(dataset.targets, device=device)
        loader = torch.utils.data.DataLoader(dataset, batch_size=32, num_workers=workers)
        source = dataset.transform
        dataset.transform = PILToTensor()
        try:
            consumed = 0
            for images, _ in loader:
                self.images[consumed:consumed + len(images)].copy_(images)
                consumed += len(images)
        finally:
            dataset.transform = source

    def __iter__(self):
        order = torch.randperm(len(self.dataset), generator=self.rng).to(self.images.device)
        for indices in order.split(self.batch_size):
            images = self.images[indices].to(dtype=torch.float32, memory_format=torch.channels_last).div_(255)
            yield images, self.labels[indices]


def train_epoch(model, loader, optimizer, scaler, device, amp):
    model.train()
    total_loss = 0.0
    for images, labels in loader:
        images = images.to(device, non_blocking=True, memory_format=torch.channels_last)
        labels = labels.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=amp):
            loss = nn.functional.cross_entropy(model(images), labels)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        total_loss += loss.detach() * labels.shape[0]
    return float(total_loss) / len(loader.dataset)


@torch.inference_mode()
def room_accuracy(model, loader, device):
    model.eval()
    correct = 0
    for images, labels in loader:
        images = images.to(device, non_blocking=True, memory_format=torch.channels_last)
        correct += (model(images).argmax(1) == labels.to(device)).sum()
    return int(correct) / len(loader.dataset)


def run(args, config, device, name, variant, positions):
    root = Path(config['dataset_folder']).resolve()
    classes = config['classes']
    key = f'{name}-{variant}'
    output = Path(config['results_dir']) / key
    output.mkdir(parents=True, exist_ok=True)
    checkpoints = args.checkpoints or Path(config['results_dir']) / 'models'
    checkpoints.mkdir(parents=True, exist_ok=True)
    best = checkpoints / f'{key}.pt'
    last = checkpoints / f'{key}.resume.pt'
    summary = output / 'metrics.json'
    spec = {
        'model': name, 'variant': variant, 'classes': classes,
        'epochs': args.epochs or config['epochs'],
        'batch_size': args.batch_size or config['batch_size'],
        'learning_rate': config['learning_rate'], 'momentum': config['momentum'],
        'seed': config['seed'], 'amp': config['amp'] and device.type == 'cuda',
    }
    if summary.exists():
        if json.loads(summary.read_text())['spec'] != spec or not best.is_file():
            raise ValueError(f'Existing outputs for {key} use another configuration or lack the checkpoint')
        print(f'Skipping completed {key}', flush=True)
        return
    seed_everything(spec['seed'])
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats(device)
    reference = LandscapeDataset(root, 'TrainingBaseline', positions, classes)
    train_set = reference if variant == 'noDA' else LandscapeDataset(root, f'TrainingDA/{variant}', None, classes)
    val_set = LandscapeDataset(root, 'Validation', None, classes)
    rng = torch.Generator()
    loader_settings = dict(batch_size=spec['batch_size'], num_workers=config['workers'],
                           pin_memory=device.type == 'cuda', persistent_workers=config['workers'] > 0)
    can_cache = (
        variant != 'noDA' and name != 'convnext_large' and device.type == 'cuda'
        and torch.cuda.mem_get_info(device)[0] > len(train_set)*3*128*512 + 2_000_000_000
    )
    if can_cache:
        train_loader = CachedBatches(train_set, device, spec['batch_size'], config['workers'], rng)
        print(f'{key}: cached uint8 training frames on GPU', flush=True)
    else:
        train_loader = torch.utils.data.DataLoader(train_set, shuffle=True, generator=rng, **loader_settings)
    val_loader = torch.utils.data.DataLoader(val_set, **loader_settings)
    state = torch.load(last, map_location='cpu', weights_only=True) if last.is_file() else None
    if state and state['spec'] != spec:
        raise ValueError(f'Checkpoint parameters differ for {key}')
    if not state and best.exists():
        raise FileExistsError(f'Found {best} without matching resume state')
    model = build(name, len(classes), pretrained=state is None).to(device, memory_format=torch.channels_last)
    optimizer = torch.optim.SGD(model.parameters(), lr=spec['learning_rate'], momentum=spec['momentum'])
    scaler = torch.amp.GradScaler(device.type, enabled=spec['amp'])
    history, best_accuracy, best_epoch = [], -1.0, 0
    if state:
        model.load_state_dict(state['weights'])
        optimizer.load_state_dict(state['optimizer'])
        scaler.load_state_dict(state['scaler'])
        history = state['history']
        if not best.is_file():
            raise FileNotFoundError(best)
        best_saved = torch.load(best, map_location='cpu', weights_only=True)
        best_accuracy, best_epoch = best_saved['validation_accuracy'], best_saved['epoch']
        del best_saved, state
    print(f'{key} using {len(train_set)} train images, {spec}', flush=True)
    for epoch in range(len(history) + 1, spec['epochs'] + 1):
        started = time.monotonic()
        epoch_seed = spec['seed'] + epoch
        seed_everything(epoch_seed)
        rng.manual_seed(epoch_seed)
        loss = train_epoch(model, train_loader, optimizer, scaler, device, spec['amp'])
        accuracy = room_accuracy(model, val_loader, device)
        history.append(dict(epoch=epoch, loss=loss, validation_accuracy=accuracy))
        if accuracy > best_accuracy:
            best_accuracy, best_epoch = accuracy, epoch
            atomic_save(dict(weights=model.state_dict(), epoch=epoch, validation_accuracy=accuracy, spec=spec), best)
        if epoch == 1 or epoch % 5 == 0 or epoch == spec['epochs']:
            if not args.best_only:
                atomic_save(dict(weights=model.state_dict(), optimizer=optimizer.state_dict(),
                                 scaler=scaler.state_dict(), history=history, spec=spec), last)
            save_json(history, output / 'history.json')
        print(f'{key} {epoch:02}/{spec["epochs"]}: loss={loss:.4f} val={accuracy:.2%} ({time.monotonic()-started:.1f}s)', flush=True)
    del optimizer, train_loader, val_loader
    state = torch.load(best, map_location='cpu', weights_only=True)
    model.load_state_dict(state['weights'])
    del state
    localizer = HierarchicalLocalizer(model, device, spec['batch_size'], reference)
    tmp = output / 'predictions.partial'
    measurements = {}
    with tmp.open('w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(('split', 'path', 'room_gt', 'room_pred', 'x_gt', 'y_gt',
                         'x_est', 'y_est', 'error_m', 'inference_ms'))
        for split in TEST_SPLITS:
            dataset = LandscapeDataset(root, split, positions, classes)
            measurements[split] = evaluate(localizer, dataset, writer)
            print(f'{key} {split}: {measurements[split]["room_accuracy"]:.2%}, MAE {measurements[split]["mae_m"]:.3f} m', flush=True)
    localizer.close()
    tmp.replace(output / 'predictions.csv')
    save_json(dict(spec=spec, best_epoch=best_epoch, best_validation_accuracy=best_accuracy,
                   train_images=len(train_set), map_images=len(reference), device=str(device),
                   gpu=torch.cuda.get_device_name(device) if device.type == 'cuda' else None,
                   peak_allocated_mib=(torch.cuda.max_memory_allocated(device) / 2**20
                                       if device.type == 'cuda' else None),
                   saved_resume_state=not args.best_only,
                   completed_at=datetime.now(timezone.utc).isoformat(), tests=measurements), summary)
    last.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('config/simulation.yaml'))
    parser.add_argument('--models', nargs='+', choices=BACKBONES)
    parser.add_argument('--variants', nargs='+', choices=VARIANTS)
    parser.add_argument('--epochs', type=int)
    parser.add_argument('--batch-size', type=int)
    parser.add_argument('--checkpoints', type=Path, help='Separate directory for large checkpoint files')
    parser.add_argument('--best-only', action='store_true', help='Keep best weights without saving optimizer state')
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    if any(value is not None and value < 1 for value in (args.epochs, args.batch_size)):
        parser.error('Epochs and batch size must be positive')
    config = yaml.safe_load(args.config.read_text())
    if not config['dataset_folder'].endswith('/') or len(config['classes']) != 7:
        parser.error('Expected a dataset path ending in / and seven class names')
    device = torch.device(args.device)
    torch.set_num_threads(2)
    if device.type == 'cuda':
        torch.backends.cudnn.benchmark = False
    positions = read_positions(Path(config['dataset_folder']))
    for variant in args.variants or config['variants']:
        for name in args.models or config['models']:
            run(args, config, device, name, variant, positions)
            if device.type == 'cuda':
                torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
