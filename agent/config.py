from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"


def config_path() -> Path:

    override = os.getenv("LCA_CONFIG")

    if override:
        return Path(override).expanduser()

    return (
        Path.home()
        / ".config"
        / "local-code-agent"
        / "config.toml"
    )


def normalize_url(url: str) -> str:

    url = url.strip()

    if not url:
        return DEFAULT_URL

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    return url.rstrip("/")


@dataclass
class Config:

    ollama_url: str = DEFAULT_URL
    model: str = DEFAULT_MODEL

    @classmethod
    def load(cls) -> "Config":

        path = config_path()

        if not path.exists():
            return cls()

        values = {}

        for line in path.read_text(
            encoding="utf-8"
        ).splitlines():

            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            values[key.strip()] = (
                value.strip()
                .strip('"')
                .strip("'")
            )

        return cls(
            ollama_url=normalize_url(
                values.get(
                    "ollama_url",
                    DEFAULT_URL,
                )
            ),
            model=values.get(
                "model",
                DEFAULT_MODEL,
            ),
        )

    def save(self) -> Path:

        path = config_path()

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            f'ollama_url = "{normalize_url(self.ollama_url)}"\n'
            f'model = "{self.model}"\n',
            encoding="utf-8",
        )

        return path