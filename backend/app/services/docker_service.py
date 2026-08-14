"""Gestione dei container dei modelli via Docker SDK.

Comunica con il docker daemon dell'host (socket montato nel container del
backend). Al momento è implementato solo l'avvio di vLLM; gli altri
framework e le WebUI sono stub che sollevano NotImplementedError finché
non vengono attivati.
"""

from __future__ import annotations

import docker
from docker.errors import DockerException, NotFound

from app.schemas import Deployment, Framework, WebUI

_VLLM_IMAGE = "vllm/vllm-openai:latest"

_client: docker.DockerClient | None = None


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def _build_vllm_command(deployment: Deployment) -> list[str]:
    cmd = [
        "--model", deployment.model_repo_id,
        "--host", "0.0.0.0",
        "--port", str(deployment.network.api_port),
    ]
    if deployment.resources.gpu_indices:
        cmd += ["--tensor-parallel-size", str(len(deployment.resources.gpu_indices))]
    if deployment.resources.offload.enabled:
        cmd += ["--cpu-offload-gb", str(deployment.resources.offload.cpu_offload_gb)]
    return cmd


def start_container(deployment: Deployment) -> str:
    """Avvia il container del modello e ritorna l'id del container Docker."""

    if deployment.framework is not Framework.VLLM:
        raise NotImplementedError(f"Framework non ancora supportato: {deployment.framework}")
    if deployment.webui is not WebUI.NONE:
        raise NotImplementedError(f"WebUI non ancora supportata: {deployment.webui}")

    client = _get_client()

    device_requests = None
    if deployment.resources.gpu_indices:
        device_requests = [
            docker.types.DeviceRequest(
                device_ids=[str(i) for i in deployment.resources.gpu_indices],
                capabilities=[["gpu"]],
            )
        ]

    container = client.containers.run(
        _VLLM_IMAGE,
        command=_build_vllm_command(deployment),
        name=f"grastorp-{deployment.id}",
        detach=True,
        ports={f"{deployment.network.api_port}/tcp": (deployment.network.bind_ip, deployment.network.api_port)},
        nano_cpus=deployment.resources.cpu_cores * 1_000_000_000,
        mem_limit=f"{deployment.resources.ram_gb}g",
        device_requests=device_requests,
        environment={"HUGGING_FACE_HUB_TOKEN": ""},
    )
    return container.id


def stop_container(container_id: str) -> None:
    client = _get_client()
    try:
        container = client.containers.get(container_id)
    except NotFound:
        return
    container.stop()
    container.remove()


def container_status(container_id: str) -> str:
    client = _get_client()
    try:
        container = client.containers.get(container_id)
    except NotFound:
        return "not_found"
    return container.status


def docker_available() -> bool:
    try:
        _get_client().ping()
        return True
    except DockerException:
        return False
