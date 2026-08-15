from app.services import docker_service

VALID_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"


def _create(client, **overrides):
    payload = {"name": "test", "model_repo_id": VALID_MODEL, **overrides}
    return client.post("/api/deployments", json=payload)


def test_get_host_security_returns_profile(client, monkeypatch):
    monkeypatch.setattr(
        docker_service,
        "get_host_security_info",
        lambda: {
            "rootless": True,
            "security_options": ["name=seccomp,profile=default", "name=rootless"],
            "experimental": False,
            "live_restore_enabled": False,
        },
    )

    resp = client.get("/api/security/host")
    assert resp.status_code == 200
    assert resp.json()["rootless"] is True


def test_get_host_security_503_when_docker_unavailable(client, monkeypatch):
    def _raise():
        raise docker_service.DockerException("boom")

    monkeypatch.setattr(docker_service, "get_host_security_info", _raise)

    resp = client.get("/api/security/host")
    assert resp.status_code == 503


def test_list_deployment_security_stopped_deployment_has_no_container_data(client):
    _create(client)

    resp = client.get("/api/security/deployments")
    assert resp.status_code == 200

    entry = resp.json()[0]
    assert entry["container_id"] is None
    assert entry["privileged"] is False
    assert entry["cap_drop"] == []


def test_list_deployment_security_running_deployment_includes_container_posture(client, monkeypatch):
    monkeypatch.setattr(docker_service, "start_container", lambda d: "container-123")
    monkeypatch.setattr(
        docker_service,
        "get_container_security",
        lambda cid: {
            "privileged": False,
            "read_only_rootfs": True,
            "user": "1000:1000",
            "cap_add": [],
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges"],
            "published_ports": ["0.0.0.0:8000->8000/tcp"],
        },
    )

    deployment_id = _create(client).json()["id"]
    client.post(f"/api/deployments/{deployment_id}/start")

    resp = client.get("/api/security/deployments")
    assert resp.status_code == 200

    entry = next(e for e in resp.json() if e["deployment_id"] == deployment_id)
    assert entry["container_id"] == "container-123"
    assert entry["read_only_rootfs"] is True
    assert entry["cap_drop"] == ["ALL"]
