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


def get_host_info() -> dict:
    """Info sul docker daemon e sull'host che lo esegue.

    Interroga direttamente il docker daemon (via il socket montato), che gira
    sull'host reale: i valori di CPU/RAM/hostname/kernel riportati sono quindi
    quelli dell'host, non quelli (limitati) del container del backend.
    """

    client = _get_client()
    info = client.info()
    version = client.version()

    return {
        "hostname": info.get("Name"),
        "operating_system": info.get("OperatingSystem"),
        "os_type": info.get("OSType"),
        "kernel_version": info.get("KernelVersion"),
        "architecture": info.get("Architecture"),
        "cpu_count": info.get("NCPU"),
        "mem_total_bytes": info.get("MemTotal"),
        "docker_version": version.get("Version"),
        "containers_total": info.get("Containers"),
        "containers_running": info.get("ContainersRunning"),
        "images_count": info.get("Images"),
    }
