"""Store dei template (modelli e registry Docker), persistito su file JSON.

Stub deliberatamente semplice: nessun ORM/DB, un file JSON su disco.
Da rivalutare quando la persistenza sqlite (in corso su un altro branch)
sarà disponibile anche per questa parte dell'app.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import Template

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TEMPLATES_FILE = DATA_DIR / "templates.json"


def _load() -> list[Template]:
    if not TEMPLATES_FILE.exists():
        return []
    raw = json.loads(TEMPLATES_FILE.read_text())
    return [Template.model_validate(item) for item in raw]


def _save(templates: list[Template]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(json.dumps([t.model_dump(mode="json") for t in templates], indent=2))


def list_templates(type_: str | None = None) -> list[Template]:
    templates = _load()
    if type_ is not None:
        templates = [t for t in templates if t.type == type_]
    return templates


def get_template(template_id: str) -> Template | None:
    return next((t for t in _load() if t.id == template_id), None)


def save_template(template: Template) -> None:
    templates = [t for t in _load() if t.id != template.id]
    templates.append(template)
    _save(templates)


def delete_template(template_id: str) -> bool:
    templates = _load()
    filtered = [t for t in templates if t.id != template_id]
    if len(filtered) == len(templates):
        return False
    _save(filtered)
    return True
