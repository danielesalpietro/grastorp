"""Store dei registry modello, persistito su file JSON (stesso pattern di datastore_store.py).

Al primo avvio (file assente) viene seminato il registry Hugging Face di
default ("huggingface"), sempre presente e non disabilitabile/eliminabile:
è la sorgente da cui provengono i template modello seminati di default.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import ModelRegistry, RegistryProvider

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REGISTRIES_FILE = DATA_DIR / "registries.json"

RESERVED_HUGGINGFACE_ID = "huggingface"
_SEED_CREATED_AT = "2024-01-01T00:00:00+00:00"

DEFAULT_REGISTRIES: list[ModelRegistry] = [
    ModelRegistry(
        id=RESERVED_HUGGINGFACE_ID,
        name="Hugging Face",
        provider=RegistryProvider.HUGGINGFACE,
        base_url="https://huggingface.co",
        enabled=True,
        created_at=_SEED_CREATED_AT,
    )
]


def _load() -> list[ModelRegistry]:
    if not REGISTRIES_FILE.exists():
        _save(DEFAULT_REGISTRIES)
        return list(DEFAULT_REGISTRIES)
    raw = json.loads(REGISTRIES_FILE.read_text())
    return [ModelRegistry.model_validate(item) for item in raw]


def _save(registries: list[ModelRegistry]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRIES_FILE.write_text(json.dumps([r.model_dump(mode="json") for r in registries], indent=2))


def list_registries() -> list[ModelRegistry]:
    return _load()


def get_registry(registry_id: str) -> ModelRegistry | None:
    return next((r for r in _load() if r.id == registry_id), None)


def save_registry(registry: ModelRegistry) -> None:
    registries = [r for r in _load() if r.id != registry.id]
    registries.append(registry)
    _save(registries)


def delete_registry(registry_id: str) -> bool:
    registries = _load()
    filtered = [r for r in registries if r.id != registry_id]
    if len(filtered) == len(registries):
        return False
    _save(filtered)
    return True
