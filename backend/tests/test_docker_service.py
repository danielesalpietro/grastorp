from app.schemas import (
    ComputeMode,
    Deployment,
    DeploymentState,
    NetworkConfig,
    OffloadConfig,
    ResourceConfig,
)
from app.services import docker_service


def _deployment(**resource_overrides) -> Deployment:
    return Deployment(
        id="dep-1",
        name="test",
        model_repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
        framework="vllm",
        webui="none",
        resources=ResourceConfig(**resource_overrides),
        network=NetworkConfig(api_port=8000),
        state=DeploymentState.STOPPED,
        created_at="2026-01-01T00:00:00Z",
    )


def test_build_command_gpu_mode_includes_tensor_parallel_and_offload():
    deployment = _deployment(
        compute_mode=ComputeMode.GPU,
        gpu_indices=[0, 1],
        offload=OffloadConfig(enabled=True, cpu_offload_gb=8),
    )
    cmd = docker_service._build_vllm_command(deployment)

    assert "--tensor-parallel-size" in cmd
    assert cmd[cmd.index("--tensor-parallel-size") + 1] == "2"
    assert "--cpu-offload-gb" in cmd
    assert cmd[cmd.index("--cpu-offload-gb") + 1] == "8.0"
    assert "--device" not in cmd


def test_build_command_gpu_mode_without_gpu_indices_skips_tensor_parallel():
    deployment = _deployment(compute_mode=ComputeMode.GPU)
    cmd = docker_service._build_vllm_command(deployment)

    assert "--tensor-parallel-size" not in cmd


def test_build_command_cpu_mode_forces_cpu_device_and_skips_gpu_flags():
    """Regressione: CPU Only non deve mai emettere flag GPU."""
    deployment = _deployment(
        compute_mode=ComputeMode.CPU,
        gpu_indices=[0],
        offload=OffloadConfig(enabled=True, cpu_offload_gb=8),
    )
    cmd = docker_service._build_vllm_command(deployment)

    assert cmd[-2:] == ["--device", "cpu"]
    assert "--tensor-parallel-size" not in cmd
    assert "--cpu-offload-gb" not in cmd


class _FakeContainer:
    id = "container-xyz"


class _FakeContainers:
    def __init__(self):
        self.run_kwargs: dict | None = None

    def run(self, *args, **kwargs):
        self.run_kwargs = kwargs
        return _FakeContainer()


class _FakeClient:
    def __init__(self):
        self.containers = _FakeContainers()


def test_start_container_gpu_mode_requests_gpu_devices(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(docker_service, "_get_client", lambda: fake_client)

    deployment = _deployment(compute_mode=ComputeMode.GPU, gpu_indices=[0])
    container_id = docker_service.start_container(deployment)

    assert container_id == "container-xyz"
    assert fake_client.containers.run_kwargs["device_requests"] is not None


def test_start_container_cpu_mode_requests_no_gpu_devices(monkeypatch):
    """Regressione: CPU Only non deve mai chiedere GPU al container."""
    fake_client = _FakeClient()
    monkeypatch.setattr(docker_service, "_get_client", lambda: fake_client)

    deployment = _deployment(compute_mode=ComputeMode.CPU)
    docker_service.start_container(deployment)

    assert fake_client.containers.run_kwargs["device_requests"] is None
