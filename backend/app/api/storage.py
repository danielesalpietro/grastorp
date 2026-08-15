from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app import datastore_store, library_config_store
from app.schemas import Datastore, DatastoreCreateRequest, LibraryConfig

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/datastores", response_model=list[Datastore])
def list_datastores() -> list[Datastore]:
    return datastore_store.list_datastores()


@router.get("/datastores/{datastore_id}", response_model=Datastore)
def get_datastore(datastore_id: str) -> Datastore:
    datastore = datastore_store.get_datastore(datastore_id)
    if datastore is None:
        raise HTTPException(status_code=404, detail="Datastore non trovato")
    return datastore


@router.post("/datastores", response_model=Datastore, status_code=201)
def create_datastore(payload: DatastoreCreateRequest) -> Datastore:
    datastore = Datastore(
        id=str(uuid.uuid4()),
        name=payload.name,
        type=payload.type,
        nfs_server=payload.nfs_server,
        nfs_export_path=payload.nfs_export_path,
        nfs_options=payload.nfs_options,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    datastore_store.save_datastore(datastore)
    return datastore


@router.delete("/datastores/{datastore_id}", status_code=204, response_model=None)
def delete_datastore(datastore_id: str) -> None:
    if library_config_store.get_config().datastore_id == datastore_id:
        raise HTTPException(status_code=409, detail="Datastore in uso dalla Model Library: non può essere eliminato")
    if not datastore_store.delete_datastore(datastore_id):
        raise HTTPException(status_code=404, detail="Datastore non trovato")


@router.get("/library/config", response_model=LibraryConfig)
def get_library_config() -> LibraryConfig:
    return library_config_store.get_config()


@router.put("/library/config", response_model=LibraryConfig)
def set_library_config(payload: LibraryConfig) -> LibraryConfig:
    if datastore_store.get_datastore(payload.datastore_id) is None:
        raise HTTPException(status_code=400, detail="Datastore non trovato")
    library_config_store.save_config(payload)
    return payload
