from app.services import docker_service

VALID_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"


def _create(client, **overrides):
    payload = {"name": "test", "model_repo_id": VALID_MODEL, **overrides}
    return client.post("/api/deployments", json=payload)


def test_create_deployment_rejects_unknown_model(client):
    resp = _create(client, model_repo_id="unknown/model")
    assert resp.status_code == 400


def test_create_deployment_with_defaults(client):
    resp = _create(client)
    assert resp.status_code == 201

    data = resp.json()
    assert data["state"] == "stopped"
    assert data["container_id"] is None
    assert data["resources"]["compute_mode"] == "gpu"


def test_create_deployment_cpu_mode_sanitizes_gpu_and_offload(client):
    """Regressione: in CPU Only, GPU e offload devono essere azzerati lato server."""
    resp = _create(
        client,
        resources={
            "compute_mode": "cpu",
            "gpu_indices": [0, 1, 2],
            "offload": {"enabled": True, "cpu_offload_gb": 8},
        },
    )
    assert resp.status_code == 201

    resources = resp.json()["resources"]
    assert resources["compute_mode"] == "cpu"
    assert resources["gpu_indices"] == []
    assert resources["offload"] == {"enabled": False, "cpu_offload_gb": 0}


def test_list_and_get_deployment(client):
    created = _create(client).json()

    listed = client.get("/api/deployments")
    assert any(d["id"] == created["id"] for d in listed.json())

    got = client.get(f"/api/deployments/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]


def test_get_missing_deployment_404(client):
    resp = client.get("/api/deployments/does-not-exist")
    assert resp.status_code == 404


def test_start_and_stop_deployment(client, monkeypatch):
    monkeypatch.setattr(docker_service, "start_container", lambda d: "container-123")
    monkeypatch.setattr(docker_service, "stop_container", lambda cid: None)

    deployment_id = _create(client).json()["id"]

    started = client.post(f"/api/deployments/{deployment_id}/start")
    assert started.status_code == 200
    assert started.json()["state"] == "running"
    assert started.json()["container_id"] == "container-123"

    stopped = client.post(f"/api/deployments/{deployment_id}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "stopped"
    assert stopped.json()["container_id"] is None


def test_start_unsupported_framework_returns_501(client, monkeypatch):
    def _raise(deployment):
        raise NotImplementedError("framework non supportato")

    monkeypatch.setattr(docker_service, "start_container", _raise)

    deployment_id = _create(client).json()["id"]

    resp = client.post(f"/api/deployments/{deployment_id}/start")
    assert resp.status_code == 501


def test_delete_deployment(client, monkeypatch):
    monkeypatch.setattr(docker_service, "stop_container", lambda cid: None)

    deployment_id = _create(client).json()["id"]

    resp = client.delete(f"/api/deployments/{deployment_id}")
    assert resp.status_code == 204

    missing = client.get(f"/api/deployments/{deployment_id}")
    assert missing.status_code == 404
