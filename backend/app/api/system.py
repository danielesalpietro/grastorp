from fastapi import APIRouter, HTTPException

from app.schemas import Framework, GPUDevice, HostInfo, NICDevice, WebUI
from app.services import docker_service, gpu_service

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/host", response_model=HostInfo)
def get_host_info() -> HostInfo:
    try:
        return HostInfo(**docker_service.get_host_info())
    except docker_service.DockerException as exc:
        raise HTTPException(status_code=503, detail=f"Docker daemon non raggiungibile: {exc}") from exc


@router.get("/gpus", response_model=list[GPUDevice])
def list_gpus() -> list[GPUDevice]:
    return gpu_service.list_gpus()


@router.get("/nics", response_model=list[NICDevice])
def list_nics() -> list[NICDevice]:
    """Stub: rilevamento NIC dell'host non ancora implementato."""
    return gpu_service.list_nics()


@router.get("/frameworks")
def list_frameworks() -> list[dict]:
    return [
        {"id": Framework.VLLM.value, "label": "vLLM", "available": True},
        {"id": Framework.TGI.value, "label": "Text Generation Inference", "available": False},
        {"id": Framework.LLAMA_CPP.value, "label": "llama.cpp", "available": False},
    ]


@router.get("/webuis")
def list_webuis() -> list[dict]:
    return [
        {"id": WebUI.NONE.value, "label": "Nessuna (solo API)", "available": True},
        {"id": WebUI.OPEN_WEBUI.value, "label": "Open WebUI", "available": False},
        {"id": WebUI.TEXT_GENERATION_WEBUI.value, "label": "Text Generation WebUI", "available": False},
    ]
