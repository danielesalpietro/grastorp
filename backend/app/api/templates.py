from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.schemas import Template, TemplateCreateRequest, TemplateFromHFRequest, TemplateType
from app import template_store
from app.services import hf_metadata_service, model_library_service

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[Template])
def list_templates(
    type_filter: TemplateType | None = Query(default=None, alias="type"),
    enabled: bool | None = Query(default=None),
) -> list[Template]:
    return template_store.list_templates(type_filter, enabled)


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
        enabled=payload.enabled,
        spec=payload.spec,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    template_store.save_template(template)
    return template


@router.post("/from-hf", response_model=Template, status_code=201)
def create_template_from_hf(payload: TemplateFromHFRequest) -> Template:
    """Crea un template modello ricavando le caratteristiche tecniche da Hugging Face Hub."""
    try:
        spec = hf_metadata_service.fetch_model_metadata(payload.repo_id)
    except hf_metadata_service.HFMetadataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    template = Template(
        id=str(uuid.uuid4()),
        type=TemplateType.MODEL,
        name=payload.name or payload.repo_id,
        description=payload.description,
        enabled=payload.enabled,
        spec=spec,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    template_store.save_template(template)
    return template


@router.post("/{template_id}/sync-hf", response_model=Template)
def sync_template_from_hf(template_id: str) -> Template:
    """Aggiorna le caratteristiche tecniche di un template modello rileggendole da Hugging Face Hub."""
    existing = template_store.get_template(template_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Template non trovato")
    if existing.type != TemplateType.MODEL:
        raise HTTPException(status_code=400, detail="Solo i template modello possono essere sincronizzati con HF")

    try:
        spec = hf_metadata_service.fetch_model_metadata(existing.spec.repo_id)
    except hf_metadata_service.HFMetadataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    updated = existing.model_copy(update={"spec": spec})
    template_store.save_template(updated)
    return updated


def _get_model_template_or_404(template_id: str) -> Template:
    template = template_store.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template non trovato")
    if template.type != TemplateType.MODEL:
        raise HTTPException(status_code=400, detail="La Library è disponibile solo per i template modello")
    return template


@router.post("/{template_id}/library/download", response_model=Template)
def download_to_library(template_id: str) -> Template:
    """Avvia (o riprende, se già in corso) il download dei pesi nel volume condiviso."""
    template = _get_model_template_or_404(template_id)
    try:
        return model_library_service.start_download(template)
    except model_library_service.ModelLibraryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{template_id}/library", response_model=Template)
def get_library_status(template_id: str) -> Template:
    """Ritorna lo stato aggiornato del download (riallineandolo con il container reale se in corso)."""
    template = _get_model_template_or_404(template_id)
    try:
        return model_library_service.get_status(template)
    except model_library_service.ModelLibraryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{template_id}/library/verify", response_model=Template)
def verify_library(template_id: str) -> Template:
    """Verifica che i file nel volume corrispondano (nome e size) a quelli attesi da Hugging Face."""
    template = _get_model_template_or_404(template_id)
    try:
        return model_library_service.verify_library(template)
    except model_library_service.ModelLibraryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/{template_id}/library", response_model=Template)
def delete_library(template_id: str) -> Template:
    """Rimuove il volume dalla Library e resetta lo stato del template."""
    template = _get_model_template_or_404(template_id)
    try:
        return model_library_service.delete_library(template)
    except model_library_service.ModelLibraryError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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
            "enabled": payload.enabled,
            "spec": payload.spec,
        }
    )
    template_store.save_template(updated)
    return updated


@router.delete("/{template_id}", status_code=204, response_model=None)
def delete_template(template_id: str) -> None:
    if not template_store.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template non trovato")
