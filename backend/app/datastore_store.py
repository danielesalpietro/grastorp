"""Store dei datastore, persistito su file JSON (stesso pattern di template_store.py).

Al primo avvio (file assente) viene seminato un datastore locale di default
("local"), sempre presente: è quello che backa la Model Library finché non
se ne configura uno condiviso (NFS).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import Datastore, DatastoreType

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATASTORES_FILE = DATA_DIR / "datastores.json"

_SEED_CREATED_AT = "2024-01-01T00:00:00+00:00"

DEFAULT_DATASTORES: list[Datastore] = [
    Datastore(
        id="local",
        name="Local Storage",
        type=DatastoreType.LOCAL,
        created_at=_SEED_CREATED_AT,
    )
]


def _load() -> list[Datastore]:
    if not DATASTORES_FILE.exists():
        _save(DEFAULT_DATASTORES)
        return list(DEFAULT_DATASTORES)
    raw = json.loads(DATASTORES_FILE.read_text())
    return [Datastore.model_validate(item) for item in raw]


def _save(datastores: list[Datastore]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATASTORES_FILE.write_text(json.dumps([d.model_dump(mode="json") for d in datastores], indent=2))


def list_datastores() -> list[Datastore]:
    return _load()


def get_datastore(datastore_id: str) -> Datastore | None:
    return next((d for d in _load() if d.id == datastore_id), None)


def save_datastore(datastore: Datastore) -> None:
    datastores = [d for d in _load() if d.id != datastore.id]
    datastores.append(datastore)
    _save(datastores)


def delete_datastore(datastore_id: str) -> bool:
    datastores = _load()
    filtered = [d for d in datastores if d.id != datastore_id]
    if len(filtered) == len(datastores):
        return False
    _save(filtered)
    return True
