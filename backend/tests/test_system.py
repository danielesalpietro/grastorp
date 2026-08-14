from app.services import docker_service, gpu_service


def test_list_frameworks_includes_vllm_available(client):
    resp = client.get("/api/system/frameworks")
    assert resp.status_code == 200

    vllm = next(f for f in resp.json() if f["id"] == "vllm")
    assert vllm["available"] is True


def test_list_webuis_only_none_available(client):
    resp = client.get("/api/system/webuis")
    assert resp.status_code == 200

    available = [w["id"] for w in resp.json() if w["available"]]
    assert available == ["none"]


def test_list_gpus_empty_when_nvidia_smi_absent(client, monkeypatch):
    monkeypatch.setattr(gpu_service.shutil, "which", lambda _: None)

    resp = client.get("/api/system/gpus")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_host_info_returns_docker_daemon_data(client, monkeypatch):
    monkeypatch.setattr(
        docker_service,
        "get_host_info",
        lambda: {
            "hostname": "test-host",
            "operating_system": "Ubuntu",
            "os_type": "linux",
            "kernel_version": "6.0",
            "architecture": "x86_64",
            "cpu_count": 8,
            "mem_total_bytes": 1024,
            "docker_version": "29.0",
            "containers_total": 0,
            "containers_running": 0,
            "images_count": 0,
        },
    )

    resp = client.get("/api/system/host")
    assert resp.status_code == 200
    assert resp.json()["hostname"] == "test-host"


def test_get_host_info_503_when_docker_unavailable(client, monkeypatch):
    def _raise():
        raise docker_service.DockerException("boom")

    monkeypatch.setattr(docker_service, "get_host_info", _raise)

    resp = client.get("/api/system/host")
    assert resp.status_code == 503
