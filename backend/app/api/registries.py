from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app import registry_store
from app.schemas import ModelRegistry, ModelRegistryCreateRequest
from app.services import hf_metadata_service

router = APIRouter(prefix="/api/registries", tags=["registries"])


@router.get("", response_model=list[ModelRegistry])
def list_registries() -> list[ModelRegistry]:
    return registry_store.list_registries()


@router.get("/{registry_id}", response_model=ModelRegistry)
def get_registry(registry_id: str) -> ModelRegistry:
    registry = registry_store.get_registry(registry_id)
    if registry is None:
        raise HTTPException(status_code=404, detail="Registry non trovato")
    return registry


@router.post("", response_model=ModelRegistry, status_code=201)
def create_registry(payload: ModelRegistryCreateRequest) -> ModelRegistry:
    registry = ModelRegistry(
        id=str(uuid.uuid4()),
        name=payload.name,
        provider=payload.provider,
        base_url=payload.base_url or "https://huggingface.co",
        api_key=payload.api_key,
        enabled=payload.enabled,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    registry_store.save_registry(registry)
    return registry


@router.put("/{registry_id}", response_model=ModelRegistry)
def update_registry(registry_id: str, payload: ModelRegistryCreateRequest) -> ModelRegistry:
    existing = registry_store.get_registry(registry_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Registry non trovato")
    if registry_id == registry_store.RESERVED_HUGGINGFACE_ID and not payload.enabled:
        raise HTTPException(status_code=409, detail="Il registry Hugging Face di default non può essere disabilitato")

    updated = existing.model_copy(
        update={
            "name": payload.name,
            "provider": payload.provider,
            "base_url": payload.base_url or existing.base_url,
            "api_key": payload.api_key,
            "enabled": payload.enabled,
        }
    )
    registry_store.save_registry(updated)
    return updated


@router.delete("/{registry_id}", status_code=204, response_model=None)
def delete_registry(registry_id: str) -> None:
    if registry_id == registry_store.RESERVED_HUGGINGFACE_ID:
        raise HTTPException(status_code=409, detail="Il registry Hugging Face di default non può essere eliminato")
    if not registry_store.delete_registry(registry_id):
        raise HTTPException(status_code=404, detail="Registry non trovato")


@router.get("/{registry_id}/search")
def search_registry_models(registry_id: str, q: str = Query(min_length=1)) -> list[dict]:
    registry = registry_store.get_registry(registry_id)
    if registry is None:
        raise HTTPException(status_code=404, detail="Registry non trovato")
    if not registry.enabled:
        raise HTTPException(status_code=400, detail="Registry disabilitato")

    try:
        return hf_metadata_service.search_models(registry, q)
    except hf_metadata_service.HFMetadataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
