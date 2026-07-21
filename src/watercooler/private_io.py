from __future__ import annotations

import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, TextIO

PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def ensure_private_directory(path: Path, *, repair_existing: bool = True) -> Path:
    """Create or validate a directory without following POSIX links."""

    directory = Path(path)
    existed = directory.exists() or directory.is_symlink()
    directory.mkdir(mode=PRIVATE_DIRECTORY_MODE, parents=True, exist_ok=True)
    if os.name != "posix":
        return directory

    flags = os.O_RDONLY
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory, flags)
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise OSError(f"private path is not a directory: {directory}")
        if repair_existing or not existed:
            os.fchmod(descriptor, PRIVATE_DIRECTORY_MODE)
    finally:
        os.close(descriptor)
    return directory


def ensure_private_regular_file(path: Path) -> Path:
    """Repair a POSIX file mode and reject linked or non-regular artifacts."""

    candidate = Path(path)
    if os.name != "posix":
        return candidate

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(candidate, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError(f"private path is not a regular file: {candidate}")
        os.fchmod(descriptor, PRIVATE_FILE_MODE)
    finally:
        os.close(descriptor)
    return candidate


def open_private_binary_update(path: Path) -> BinaryIO:
    """Open a persistent binary artifact with owner-only POSIX permissions."""

    destination = Path(path)
    ensure_private_directory(destination.parent)
    flags = os.O_RDWR | os.O_CREAT
    if os.name == "posix":
        flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(destination, flags, PRIVATE_FILE_MODE)
    try:
        if os.name == "posix":
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError(f"private path is not a regular file: {destination}")
            os.fchmod(descriptor, PRIVATE_FILE_MODE)
        handle = os.fdopen(descriptor, "r+b")
        descriptor = -1
        return handle
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def atomic_write_private_text(path: Path, value: str) -> None:
    """Atomically replace one text file with owner-only POSIX permissions."""

    destination = Path(path)
    ensure_private_directory(destination.parent)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, PRIVATE_FILE_MODE)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        ensure_private_regular_file(destination)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


@contextmanager
def open_private_text_writer(path: Path) -> Iterator[TextIO]:
    """Open a streamed text artifact without following a POSIX symlink."""

    destination = Path(path)
    ensure_private_directory(destination.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if os.name == "posix":
        flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(destination, flags, PRIVATE_FILE_MODE)
    try:
        if os.name == "posix":
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError(f"private path is not a regular file: {destination}")
            os.fchmod(descriptor, PRIVATE_FILE_MODE)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            yield handle
    finally:
        if descriptor >= 0:
            os.close(descriptor)
