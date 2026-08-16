"""Validate the portable shape and Lambda size limits of a deployment archive."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

MAX_ZIPPED_BYTES = 50 * 1024 * 1024
MAX_UNZIPPED_BYTES = 250 * 1024 * 1024
REQUIRED_ENTRIES = (
    "app/__init__.py",
    "app/lambda_handler.py",
    "mangum/__init__.py",
    "openai/__init__.py",
    "psycopg/__init__.py",
)
PSYCOPG_BINARY_PREFIX = "psycopg_binary/_psycopg.cpython-312-x86_64-linux-gnu"


def validate_archive(archive_path: Path) -> tuple[int, int]:
    zipped_bytes = archive_path.stat().st_size
    if zipped_bytes > MAX_ZIPPED_BYTES:
        raise ValueError(
            f"zip is {zipped_bytes} bytes; direct Lambda upload limit is {MAX_ZIPPED_BYTES}"
        )

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        missing = [entry for entry in REQUIRED_ENTRIES if entry not in names]
        if missing:
            raise ValueError(f"archive is missing required entries: {', '.join(missing)}")

        if not any(
            name.startswith(PSYCOPG_BINARY_PREFIX) and name.endswith(".so") for name in names
        ):
            raise ValueError("archive is missing the CPython 3.12 x86_64 psycopg binary extension")

        unsafe = [name for name in names if name.startswith("/") or ".." in Path(name).parts]
        if unsafe:
            raise ValueError(f"archive contains unsafe paths: {', '.join(sorted(unsafe))}")

        unzipped_bytes = sum(entry.file_size for entry in archive.infolist())

    if unzipped_bytes > MAX_UNZIPPED_BYTES:
        raise ValueError(
            f"unzipped content is {unzipped_bytes} bytes; Lambda limit is {MAX_UNZIPPED_BYTES}"
        )
    return zipped_bytes, unzipped_bytes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()

    try:
        zipped_bytes, unzipped_bytes = validate_archive(args.archive)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"INVALID_LAMBDA_ZIP: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"ZIP_BYTES={zipped_bytes}")
    print(f"UNZIPPED_BYTES={unzipped_bytes}")
    print("HANDLER=app.lambda_handler.handler")
    print("ARCHITECTURE=x86_64")


if __name__ == "__main__":
    main()
