"""Configuration loader with dot-path access (R-01).

Loads assistant_config.yml and exposes settings via attribute access,
e.g. config.llm.provider, config.tts.voice.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "assistant_config.yml"


class ConfigNode:
    """Recursive wrapper that turns a dict into an object with attribute access."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigNode(value))
            else:
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f"ConfigNode({self._data!r})"

    def __getattr__(self, name: str) -> Any:
        # Only intercept keys that exist in the underlying data as dicts
        # (i.e. sub-sections). For anything else, raise AttributeError so
        # that getattr(obj, key, default) works correctly.
        if name.startswith("_"):
            raise AttributeError(name)
        raise AttributeError(
            f"Config has no attribute {name!r}. "
            f"Available keys: {', '.join(sorted(self._data)) or '(none)'}"
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key* if present, else *default*."""
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def to_dict(self) -> dict[str, Any]:
        """Return the raw dictionary."""
        return self._data


def load_config(path: Path | str | None = None) -> ConfigNode:
    """Load YAML config and return a ConfigNode with dot-path access.

    Parameters
    ----------
    path:
        Path to the YAML config file.  Defaults to ``assistant_config.yml``
        in the project root.

    Raises
    ------
    FileNotFoundError
        If the config file does not exist.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return ConfigNode(data)
