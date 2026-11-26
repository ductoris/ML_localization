"""Infer the room and metric position of one panorama."""
import argparse
import json
from pathlib import Path

from PIL import Image
import torch
from torchvision.transforms import ToTensor
import yaml

from eval.sim_localization import HierarchicalLocalizer, LandscapeDataset, read_positions
from train.sim_experiment import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('--config', type=Path, default=Path('config/simulation.yaml'))
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    cfg = yaml.safe_load(args.config.read_text())
    root = Path(cfg['dataset_folder']).resolve()
    device = torch.device(args.device)
    saved = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    spec = saved['spec']
    if spec['classes'] != cfg['classes']:
        parser.error('Checkpoint classes differ from the dataset')
    model = build(spec['model'], len(spec['classes']), pretrained=False)
    model.load_state_dict(saved['weights'])
    model.to(device, memory_format=torch.channels_last)
    reference = LandscapeDataset(root, 'TrainingBaseline', read_positions(root), spec['classes'])
    localizer = HierarchicalLocalizer(model, device, 16, reference)
    try:
        with Image.open(args.image) as image:
            if image.size != (512, 128):
                parser.error('Expected a panorama of 512×128 pixels')
            tensor = ToTensor()(image.convert('RGB')).unsqueeze(0)
        room, (x, y) = localizer.predict(localizer.to_device(tensor))
        print(json.dumps({'room_pred': reference.classes[room], 'x_est_m': x, 'y_est_m': y, 'frame': 'house'}))
    finally:
        localizer.close()


if __name__ == '__main__':
    main()
