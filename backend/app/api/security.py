from fastapi import APIRouter, HTTPException

from app import store
from app.schemas import ContainerSecurity, HostSecurityProfile
from app.services import docker_service

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/host", response_model=HostSecurityProfile)
def get_host_security() -> HostSecurityProfile:
    """Security Profile del docker daemon, l'equivalente del Security Profile ESXi."""
    try:
        return HostSecurityProfile(**docker_service.get_host_security_info())
    except docker_service.DockerException as exc:
        raise HTTPException(status_code=503, detail=f"Docker daemon non raggiungibile: {exc}") from exc


@router.get("/deployments", response_model=list[ContainerSecurity])
def list_deployment_security() -> list[ContainerSecurity]:
    """Postura di sicurezza per deployment, l'equivalente delle impostazioni di sicurezza per-VM in ESXi."""
    result = []
    for deployment in store.list_deployments():
        security = docker_service.get_container_security(deployment.container_id) if deployment.container_id else None
        result.append(
            ContainerSecurity(
                deployment_id=deployment.id,
                deployment_name=deployment.name,
                container_id=deployment.container_id,
                **(security or {}),
            )
        )
    return result
