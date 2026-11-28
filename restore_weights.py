"""Restore a checkpoint from the files in results/office/models/parts."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile


def restore(manifest: Path, output_dir: Path) -> None:
    info = json.loads(manifest.read_text())
    names = [info["file"], *info["parts"]]
    if any(Path(name).name != name or name in ("", ".", "..") for name in names):
        raise ValueError(f"Invalid filename in {manifest}")
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / info["file"]
    if destination.exists():
        raise FileExistsError(destination)
    digest = hashlib.sha256()
    size = 0
    with NamedTemporaryFile(dir=output_dir, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            for name in info["parts"]:
                with (manifest.parent / name).open("rb") as part:
                    while block := part.read(1024 * 1024):
                        handle.write(block)
                        digest.update(block)
                        size += len(block)
            if size != info["bytes"] or digest.hexdigest() != info["sha256"]:
                raise ValueError(f"Checksum or file size differs from {manifest}")
            handle.close()
            destination.hardlink_to(temporary)
        finally:
            temporary.unlink(missing_ok=True)
    print(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results/office/models"))
    args = parser.parse_args()
    restore(args.manifest, args.output_dir)
