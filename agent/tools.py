from __future__ import annotations

import subprocess
from pathlib import Path


MAX_RESULTS = 50
MAX_FILE_CHARS = 30_000
MAX_OUTPUT_CHARS = 40_000


EXCLUDES = [
    "--glob", "!.git",
    "--glob", "!node_modules",
    "--glob", "!target",
    "--glob", "!build",
    "--glob", "!dist",
    "--glob", "!vendor",
    "--glob", "!bin",
    "--glob", "!obj",
    "--glob", "!__pycache__",
]


def run(
    command: list[str],
    cwd: Path,
):
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return (
        result.stdout,
        result.stderr,
        result.returncode,
    )


def search_code(
    repo: Path,
    query: str,
    file_types=None,
) -> str:

    if not query:
        return "ERROR: query is required."

    command = [
        "rg",
        "--line-number",
        "--column",
        "--hidden",
        *EXCLUDES,
    ]

    for extension in file_types or []:

        extension = extension.lstrip(".")

        command += [
            "--glob",
            f"*.{extension}",
        ]

    command.append(query)

    stdout, stderr, code = run(
        command,
        repo,
    )

    if code not in (0, 1):
        return f"Search failed:\n{stderr}"

    lines = stdout.splitlines()

    lines = lines[:MAX_RESULTS]

    if not lines:
        return "No matches found."

    return "\n".join(lines)[
        :MAX_OUTPUT_CHARS
    ]


def find_files(
    repo: Path,
    pattern: str,
) -> str:

    if not pattern:
        return "ERROR: pattern is required."

    stdout, stderr, code = run(
        [
            "rg",
            "--files",
            "--hidden",
            *EXCLUDES,
        ],
        repo,
    )

    if code != 0:
        return f"File search failed:\n{stderr}"

    matches = []

    for line in stdout.splitlines():

        if pattern.lower() in line.lower():

            matches.append(line)

        if len(matches) >= MAX_RESULTS:
            break

    if not matches:
        return "No files found."

    return "\n".join(matches)


def safe_path(
    repo: Path,
    relative: str,
) -> Path:

    root = repo.resolve()

    path = (
        root / relative
    ).resolve()

    # Prevent ../../evil.txt
    path.relative_to(root)

    return path


def read_file(
    repo: Path,
    path: str,
) -> str:

    try:
        file_path = safe_path(
            repo,
            path,
        )

    except ValueError:
        return (
            "ERROR: path is outside "
            "repository."
        )

    if not file_path.exists():
        return "ERROR: file does not exist."

    if not file_path.is_file():
        return "ERROR: path is not a file."

    try:
        data = file_path.read_bytes()

        # Probably binary.
        if b"\x00" in data[:4096]:
            return (
                "ERROR: file appears "
                "to be binary."
            )

        text = data.decode(
            "utf-8",
            errors="replace",
        )

    except OSError as exc:
        return f"ERROR reading file: {exc}"

    if len(text) > MAX_FILE_CHARS:

        text = (
            text[:MAX_FILE_CHARS]
            + "\n\n[FILE TRUNCATED]"
        )

    return text


def git_status(repo: Path) -> str:

    stdout, stderr, code = run(
        [
            "git",
            "status",
            "--short",
        ],
        repo,
    )

    if code != 0:
        return f"Git status failed:\n{stderr}"

    if not stdout:
        return "Working tree clean."

    return stdout


def git_diff(repo: Path) -> str:

    stdout, stderr, code = run(
        [
            "git",
            "diff",
        ],
        repo,
    )

    if code != 0:
        return f"Git diff failed:\n{stderr}"

    if not stdout:
        return "No changes."

    return stdout[:MAX_OUTPUT_CHARS]


TOOLS = [

    {
        "type": "function",
        "function": {
            "name": "search_code",

            "description": (
                "Search repository contents for "
                "text, symbols, classes, functions, "
                "strings, references, or configuration."
            ),

            "parameters": {
                "type": "object",

                "required": [
                    "query"
                ],

                "properties": {

                    "query": {
                        "type": "string"
                    },

                    "file_types": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                    },
                },
            },
        },
    },

    {
        "type": "function",
        "function": {

            "name": "find_files",

            "description": (
                "Find repository files by "
                "filename or partial path."
            ),

            "parameters": {
                "type": "object",

                "required": [
                    "pattern"
                ],

                "properties": {

                    "pattern": {
                        "type": "string"
                    }
                },
            },
        },
    },

    {
        "type": "function",
        "function": {

            "name": "read_file",

            "description": (
                "Read a text file inside "
                "the repository."
            ),

            "parameters": {
                "type": "object",

                "required": [
                    "path"
                ],

                "properties": {

                    "path": {
                        "type": "string"
                    }
                },
            },
        },
    },

    {
        "type": "function",
        "function": {

            "name": "git_status",

            "description": (
                "Show Git working tree status."
            ),

            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },

    {
        "type": "function",
        "function": {

            "name": "git_diff",

            "description": (
                "Show the current uncommitted "
                "Git diff."
            ),

            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]