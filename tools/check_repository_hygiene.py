"""Check that generated artifacts and local-only files are not tracked."""

from __future__ import annotations

import subprocess
import sys
from pathlib import PurePosixPath


BLOCKED_DIRS = {
    ".pytest_cache",
    ".vite",
    "__pycache__",
    "bin",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "obj",
}

BLOCKED_SUFFIXES = {
    ".db",
    ".log",
    ".pid",
    ".pyc",
    ".sqlite",
    ".sqlite3",
}

BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "yarn.lock",
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        text=False,
    )
    return [
        path.decode("utf-8", errors="replace")
        for path in result.stdout.split(b"\0")
        if path
    ]


def is_blocked(path: str) -> bool:
    parsed = PurePosixPath(path)
    parts = set(parsed.parts)
    filename = parsed.name

    return (
        bool(parts & BLOCKED_DIRS)
        or filename in BLOCKED_FILENAMES
        or any(filename.endswith(suffix) for suffix in BLOCKED_SUFFIXES)
    )


def main() -> int:
    offenders = sorted(path for path in tracked_files() if is_blocked(path))
    if not offenders:
        print("Repository hygiene check passed.")
        return 0

    print("Repository hygiene check failed: generated or local-only files are tracked.")
    print("Remove them from the Git index and keep the working copies local.")
    for path in offenders:
        print(f"- {path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
