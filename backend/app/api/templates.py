from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.schemas import Template, TemplateCreateRequest, TemplateType
from app import template_store

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[Template])
def list_templates(type_filter: TemplateType | None = Query(default=None, alias="type")) -> list[Template]:
    return template_store.list_templates(type_filter)


@router.get("/{template_id}", response_model=Template)
def get_template(template_id: str) -> Template:
    template = template_store.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template non trovato")
    return template


@router.post("", response_model=Template, status_code=201)
def create_template(payload: TemplateCreateRequest) -> Template:
    template = Template(
        id=str(uuid.uuid4()),
        type=payload.type,
        name=payload.name,
        description=payload.description,
        spec=payload.spec,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    template_store.save_template(template)
    return template


@router.put("/{template_id}", response_model=Template)
def update_template(template_id: str, payload: TemplateCreateRequest) -> Template:
    existing = template_store.get_template(template_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Template non trovato")

    updated = existing.model_copy(
        update={
            "type": payload.type,
            "name": payload.name,
            "description": payload.description,
            "spec": payload.spec,
        }
    )
    template_store.save_template(updated)
    return updated


@router.delete("/{template_id}", status_code=204, response_model=None)
def delete_template(template_id: str) -> None:
    if not template_store.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template non trovato")
