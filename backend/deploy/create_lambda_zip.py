"""Create a byte-for-byte stable Lambda zip from a prepared package directory."""

from __future__ import annotations

import argparse
import stat
import zipfile
from pathlib import Path

ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
FILE_MODE = stat.S_IFREG | 0o644


def create_archive(package_dir: Path, output_path: Path) -> None:
    package_dir = package_dir.resolve(strict=True)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        output_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source_path in sorted(path for path in package_dir.rglob("*") if path.is_file()):
            relative_path = source_path.relative_to(package_dir).as_posix()
            entry = zipfile.ZipInfo(relative_path, date_time=ZIP_EPOCH)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = FILE_MODE << 16
            archive.writestr(entry, source_path.read_bytes(), compresslevel=9)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()
    create_archive(args.package_dir, args.output_path)


if __name__ == "__main__":
    main()
