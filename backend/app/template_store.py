"""Store dei template (modelli e registry Docker), persistito su file JSON.

Stub deliberatamente semplice: nessun ORM/DB, un file JSON su disco.
Da rivalutare quando la persistenza sqlite (in corso su un altro branch)
sarà disponibile anche per questa parte dell'app.

Al primo avvio (file assente) il file viene inizializzato con i 3 modelli MoE
già noti, come template abilitati: chi li elimina o disabilita non se li
ritrova ricreati al giro successivo, il seed serve solo a popolare il primo
avvio a vuoto.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import ModelTemplateSpec, Template, TemplateType

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TEMPLATES_FILE = DATA_DIR / "templates.json"

_SEED_CREATED_AT = "2024-01-01T00:00:00+00:00"

DEFAULT_MODEL_TEMPLATES: list[Template] = [
    Template(
        id="seed-mixtral-8x7b",
        type=TemplateType.MODEL,
        name="Mixtral 8x7B Instruct",
        description="Mixture-of-Experts di Mistral AI, 8 esperti da 7B, 2 attivi per token.",
        enabled=True,
        spec=ModelTemplateSpec(
            repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
            architecture="mixtral",
            num_experts=8,
            num_experts_active=2,
            params_billion=46.7,
        ),
        created_at=_SEED_CREATED_AT,
    ),
    Template(
        id="seed-mixtral-8x22b",
        type=TemplateType.MODEL,
        name="Mixtral 8x22B Instruct",
        description="Variante Mixtral su larga scala, 8 esperti da 22B.",
        enabled=True,
        spec=ModelTemplateSpec(
            repo_id="mistralai/Mixtral-8x22B-Instruct-v0.1",
            architecture="mixtral",
            num_experts=8,
            num_experts_active=2,
            params_billion=141.0,
        ),
        created_at=_SEED_CREATED_AT,
    ),
    Template(
        id="seed-deepseek-moe-16b",
        type=TemplateType.MODEL,
        name="DeepSeek-MoE 16B Chat",
        description="MoE fine-grained di DeepSeek con routing su 64 esperti.",
        enabled=True,
        spec=ModelTemplateSpec(
            repo_id="deepseek-ai/deepseek-moe-16b-chat",
            architecture="deepseek",
            num_experts=64,
            params_billion=16.4,
        ),
        created_at=_SEED_CREATED_AT,
    ),
]


def _load() -> list[Template]:
    if not TEMPLATES_FILE.exists():
        _save(DEFAULT_MODEL_TEMPLATES)
        return list(DEFAULT_MODEL_TEMPLATES)
    raw = json.loads(TEMPLATES_FILE.read_text())
    return [Template.model_validate(item) for item in raw]


def _save(templates: list[Template]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(json.dumps([t.model_dump(mode="json") for t in templates], indent=2))


def list_templates(type_: str | None = None, enabled: bool | None = None) -> list[Template]:
    templates = _load()
    if type_ is not None:
        templates = [t for t in templates if t.type == type_]
    if enabled is not None:
        templates = [t for t in templates if t.enabled == enabled]
    return templates


def get_template(template_id: str) -> Template | None:
    return next((t for t in _load() if t.id == template_id), None)


def get_enabled_model_template_by_repo_id(repo_id: str) -> Template | None:
    return next(
        (
            t
            for t in _load()
            if t.type == TemplateType.MODEL and t.enabled and isinstance(t.spec, ModelTemplateSpec) and t.spec.repo_id == repo_id
        ),
        None,
    )


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
