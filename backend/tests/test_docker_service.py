from docker.errors import NotFound

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


class _FakeNetwork:
    def __init__(self, attrs: dict):
        self.attrs = attrs


class _FakeNetworksApi:
    def __init__(self, networks: list[_FakeNetwork]):
        self._networks = networks

    def list(self):
        return self._networks


def test_list_networks_maps_driver_subnet_and_containers(monkeypatch):
    fake_network = _FakeNetwork(
        {
            "Id": "abcdef0123456789",
            "Name": "grastorp_default",
            "Driver": "bridge",
            "Scope": "local",
            "Internal": False,
            "Attachable": True,
            "IPAM": {"Config": [{"Subnet": "172.20.0.0/16", "Gateway": "172.20.0.1"}]},
            "Containers": {"c1": {"Name": "grastorp-dep-1"}},
        }
    )
    fake_client = _FakeClient()
    fake_client.networks = _FakeNetworksApi([fake_network])
    monkeypatch.setattr(docker_service, "_get_client", lambda: fake_client)

    networks = docker_service.list_networks()

    assert networks == [
        {
            "id": "abcdef012345",
            "name": "grastorp_default",
            "driver": "bridge",
            "scope": "local",
            "subnet": "172.20.0.0/16",
            "gateway": "172.20.0.1",
            "internal": False,
            "attachable": True,
            "containers": ["grastorp-dep-1"],
        }
    ]


def test_get_host_security_info_detects_rootless_and_security_options(monkeypatch):
    fake_client = _FakeClient()
    fake_client.info = lambda: {
        "SecurityOptions": ["name=seccomp,profile=default", "name=rootless"],
        "ExperimentalBuild": False,
        "LiveRestoreEnabled": True,
    }
    monkeypatch.setattr(docker_service, "_get_client", lambda: fake_client)

    info = docker_service.get_host_security_info()

    assert info["rootless"] is True
    assert info["security_options"] == ["name=seccomp,profile=default", "name=rootless"]
    assert info["live_restore_enabled"] is True


def test_get_host_security_info_not_rootless_by_default(monkeypatch):
    fake_client = _FakeClient()
    fake_client.info = lambda: {"SecurityOptions": ["name=seccomp,profile=default", "name=apparmor"]}
    monkeypatch.setattr(docker_service, "_get_client", lambda: fake_client)

    info = docker_service.get_host_security_info()

    assert info["rootless"] is False


class _FakeSecurityContainer:
    def __init__(self, attrs: dict):
        self.attrs = attrs


class _FakeContainersWithGet(_FakeContainers):
    def __init__(self, container: _FakeSecurityContainer | None):
        super().__init__()
        self._container = container

    def get(self, container_id: str):
        if self._container is None:
            raise NotFound("not found")
        return self._container


def test_get_container_security_maps_capabilities_and_published_ports(monkeypatch):
    container = _FakeSecurityContainer(
        {
            "HostConfig": {
                "Privileged": False,
                "ReadonlyRootfs": True,
                "CapAdd": ["NET_ADMIN"],
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges"],
            },
            "Config": {"User": "1000:1000"},
            "NetworkSettings": {
                "Ports": {"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]}
            },
        }
    )
    fake_client = _FakeClient()
    fake_client.containers = _FakeContainersWithGet(container)
    monkeypatch.setattr(docker_service, "_get_client", lambda: fake_client)

    security = docker_service.get_container_security("container-xyz")

    assert security == {
        "privileged": False,
        "read_only_rootfs": True,
        "user": "1000:1000",
        "cap_add": ["NET_ADMIN"],
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges"],
        "published_ports": ["0.0.0.0:8000->8000/tcp"],
    }


def test_get_container_security_returns_none_when_container_not_found(monkeypatch):
    fake_client = _FakeClient()
    fake_client.containers = _FakeContainersWithGet(None)
    monkeypatch.setattr(docker_service, "_get_client", lambda: fake_client)

    assert docker_service.get_container_security("missing") is None
