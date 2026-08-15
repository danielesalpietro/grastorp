from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.schemas import ComputeMode, Deployment, DeploymentCreateRequest, DeploymentState, LibraryStatus, OffloadConfig
from app.services import docker_service
from app import store, template_store

router = APIRouter(prefix="/api/deployments", tags=["deployments"])


@router.get("", response_model=list[Deployment])
def list_deployments() -> list[Deployment]:
    return store.list_deployments()


@router.post("", response_model=Deployment, status_code=201)
def create_deployment(payload: DeploymentCreateRequest) -> Deployment:
    template = template_store.get_enabled_model_template_by_repo_id(payload.model_repo_id)
    if template is None:
        raise HTTPException(status_code=400, detail="Modello non presente tra i template abilitati")

    library_status = template.spec.library_status
    if library_status is LibraryStatus.DOWNLOADING:
        raise HTTPException(status_code=409, detail="Il modello è ancora in fase di download nella Library")
    if library_status is LibraryStatus.ERROR:
        raise HTTPException(
            status_code=409, detail="Il download del modello nella Library ha un errore: verificalo nella pagina Templates"
        )

    if payload.resources.compute_mode is ComputeMode.CPU:
        # In CPU Only, GPU e CPU offload non sono applicabili: li azzeriamo
        # indipendentemente da cosa manda il client.
        payload.resources.gpu_indices = []
        payload.resources.offload = OffloadConfig()

    deployment = Deployment(
        id=str(uuid.uuid4()),
        name=payload.name,
        model_repo_id=payload.model_repo_id,
        framework=payload.framework,
        webui=payload.webui,
        resources=payload.resources,
        network=payload.network,
        state=DeploymentState.STOPPED,
        library_volume=template.spec.volume_name if library_status is LibraryStatus.READY else None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    store.save_deployment(deployment)
    return deployment


@router.get("/{deployment_id}", response_model=Deployment)
def get_deployment(deployment_id: str) -> Deployment:
    deployment = store.get_deployment(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment non trovato")
    return deployment


@router.delete("/{deployment_id}", status_code=204, response_model=None)
def delete_deployment(deployment_id: str) -> None:
    deployment = store.get_deployment(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment non trovato")
    if deployment.container_id:
        docker_service.stop_container(deployment.container_id)
    store.delete_deployment(deployment_id)


@router.post("/{deployment_id}/start", response_model=Deployment)
def start_deployment(deployment_id: str) -> Deployment:
    deployment = store.get_deployment(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment non trovato")

    try:
        container_id = docker_service.start_container(deployment)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    deployment.container_id = container_id
    deployment.state = DeploymentState.RUNNING
    store.save_deployment(deployment)
    return deployment


@router.post("/{deployment_id}/stop", response_model=Deployment)
def stop_deployment(deployment_id: str) -> Deployment:
    deployment = store.get_deployment(deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment non trovato")

    if deployment.container_id:
        docker_service.stop_container(deployment.container_id)
        deployment.container_id = None
    deployment.state = DeploymentState.STOPPED
    store.save_deployment(deployment)
    return deployment
