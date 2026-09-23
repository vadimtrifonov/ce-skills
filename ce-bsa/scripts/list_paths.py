#!/usr/bin/env python3
"""Print file paths from a BSA or BA2 without the BSArch header."""

from __future__ import annotations

import argparse
import errno
import os
import re
import subprocess
import sys
from pathlib import Path

_FILES_RE = re.compile(r"^\s*Files:\s*(\d+)\s*$")


class ListOutputError(ValueError):
    """BSArch list output does not match its expected structure."""


def parse_list_output(output: str) -> list[str]:
    """Parse file paths and require their count to match BSArch's ``Files:`` count."""
    lines = output.splitlines()

    count_index = -1
    expected_count = -1
    for index, line in enumerate(lines):
        match = _FILES_RE.match(line)
        if match:
            count_index = index
            expected_count = int(match.group(1))
            break

    if count_index < 0:
        raise ListOutputError("BSArch output has no 'Files:' count")

    separator_index = next(
        (
            index
            for index in range(count_index + 1, len(lines))
            if not lines[index].strip()
        ),
        None,
    )
    if separator_index is None:
        raise ListOutputError("BSArch output has no blank line before its file list")

    paths = [line for line in lines[separator_index + 1 :] if line.strip()]
    if len(paths) != expected_count:
        raise ListOutputError(
            f"BSArch declared {expected_count} files but listed {len(paths)}"
        )

    return [path.replace("\\", "/") for path in paths]


def list_paths(archive: Path) -> list[str]:
    """Run BSArch and return the file paths that it reports."""
    if not archive.is_file():
        raise FileNotFoundError(f"archive does not exist or is not a file: {archive}")

    try:
        result = subprocess.run(
            ["BSArch64.exe", str(archive), "-list"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        raise FileNotFoundError(
            "BSArch64.exe is not available; run this helper through 'mise exec --'"
        ) from error

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"BSArch failed with exit code {result.returncode}{suffix}")

    return parse_list_output(result.stdout)


def _redirect_stdout_to_null() -> None:
    """Prevent another write to a pipe that its reader closed."""
    try:
        stdout_fd = sys.stdout.fileno()
        null_fd = os.open(os.devnull, os.O_WRONLY)
    except (AttributeError, OSError):
        return

    try:
        os.dup2(null_fd, stdout_fd)
    finally:
        os.close(null_fd)


def write_paths(paths: list[str]) -> None:
    """Print file paths and stop cleanly if a pipeline reader exits early."""
    try:
        for path in paths:
            sys.stdout.write(f"{path}\n")
        sys.stdout.flush()
    except BrokenPipeError:
        _redirect_stdout_to_null()
    except OSError as error:
        if os.name != "nt" or error.errno != errno.EINVAL:
            raise
        _redirect_stdout_to_null()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "List file paths from a BSA or BA2, one per line, without the "
            "BSArch header. Backslashes are changed to forward slashes."
        )
    )
    parser.add_argument("archive", type=Path, help="BSA or BA2 archive to list")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        paths = list_paths(args.archive)
    except (FileNotFoundError, ListOutputError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    write_paths(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
