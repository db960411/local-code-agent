from __future__ import annotations

import subprocess
from pathlib import Path


def git_root(
    start: Path | None = None,
) -> Path | None:

    current = (
        start or Path.cwd()
    ).resolve()

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(current),
                "rev-parse",
                "--show-toplevel",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )

    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return None

    if result.returncode != 0:
        return None

    path = result.stdout.strip()

    if not path:
        return None

    return Path(path).resolve()