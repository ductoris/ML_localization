"""Collect completed simulation measurements into one CSV and Markdown table."""
import argparse
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory


def summarize(outputs):
    fields = ('model', 'variant', 'epochs', 'batch_size', 'amp', 'best_epoch',
              'best_validation_accuracy_pct', 'split', 'samples', 'room_accuracy_pct',
              'mae_m', 'variance_m2', 'rmse_m', 'inference_ms')
    results = []
    rooms = []
    for source in sorted(outputs.glob('*/metrics.json')):
        info = json.loads(source.read_text())
        settings = info['spec']
        for split, metrics in info['tests'].items():
            results.append((
                settings['model'], settings['variant'], settings['epochs'], settings['batch_size'],
                settings['amp'], info['best_epoch'], info['best_validation_accuracy'] * 100, split,
                metrics['n'], metrics['room_accuracy'] * 100, metrics['mae_m'], metrics['variance_m2'],
                metrics['rmse_m'], metrics['inference_ms'],
            ))
            for index, room in enumerate(settings['classes']):
                confusions = metrics['confusion'][index]
                total = sum(confusions)
                rooms.append((settings['model'], settings['variant'], split, room, total,
                              100 * confusions[index] / total if total else None))
    if not results:
        raise ValueError(f'No completed metrics found in {outputs}')
    results.sort(key=lambda row: (row[0], row[1] != 'noDA', row[1]))
    lines = [
        '# Kết quả định vị mô phỏng',
        '',
        '| Mô hình | Dữ liệu train | Tập test | Số ảnh | Accuracy phòng | MAE (m) | Phương sai (m²) | RMSE (m) | ms/ảnh |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    for name, variant, _, _, _, _, _, split, count, accuracy, mae, variance, rmse, latency in results:
        lines.append(
            f'| {name} | {variant} | {split} | {count} | {accuracy:.2f}% | '
            f'{mae:.3f} | {variance:.3f} | {rmse:.3f} | {latency:.3f} |'
        )
    with TemporaryDirectory(prefix='.summary-', dir=outputs) as directory:
        staged = Path(directory)
        with (staged / 'summary.csv').open('w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows(results)
        with (staged / 'room-accuracy.csv').open('w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(('model', 'variant', 'split', 'room', 'samples', 'room_accuracy_pct'))
            writer.writerows(rooms)
        (staged / 'summary.md').write_text('\n'.join(lines) + '\n')
        for name in ('summary.csv', 'summary.md', 'room-accuracy.csv'):
            (staged / name).replace(outputs / name)
    print(f'{len(results)} test measurements in {outputs / "summary.csv"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path, nargs='?', default=Path('data/sim-results-office'))
    args = parser.parse_args()
    summarize(args.results)


if __name__ == '__main__':
    main()
