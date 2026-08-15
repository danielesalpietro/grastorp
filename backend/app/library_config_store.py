"""Impostazione (singleton) di quale datastore ospita la Model Library condivisa."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import LibraryConfig

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LIBRARY_CONFIG_FILE = DATA_DIR / "library_config.json"


def get_config() -> LibraryConfig:
    if not LIBRARY_CONFIG_FILE.exists():
        return LibraryConfig()
    return LibraryConfig.model_validate(json.loads(LIBRARY_CONFIG_FILE.read_text()))


def save_config(config: LibraryConfig) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARY_CONFIG_FILE.write_text(json.dumps(config.model_dump(mode="json"), indent=2))
