from app.schemas import LibraryStatus, ModelTemplateSpec, Template
from app.services import hf_metadata_service, model_library_service

MODEL_PAYLOAD = {
    "type": "model",
    "name": "Mixtral 8x22B",
    "description": "MoE su larga scala",
    "spec": {
        "repo_id": "mistralai/Mixtral-8x22B-Instruct-v0.1",
        "architecture": "mixtral",
        "num_experts": 8,
        "num_experts_active": 2,
        "num_layers": 56,
        "params_billion": 141.0,
        "shard_size_gb": 17.6,
        "num_shards": 8,
        "context_length": 65536,
        "quantization": "fp16",
    },
}

DOCKER_PAYLOAD = {
    "type": "docker_registry",
    "name": "vLLM OpenAI-compatible server",
    "description": "Container pronto per il deploy",
    "spec": {
        "registry": "ghcr.io",
        "image": "vllm/vllm-openai",
        "tag": "latest",
        "size_gb": 6.2,
        "ram_required_mb": 16384,
        "gpu_required": True,
        "gpu_compatible": ["nvidia-ampere", "nvidia-hopper"],
        "min_vram_mb": 24576,
        "cuda_version": "12.1",
    },
}


def test_list_templates_seeded_with_default_models_by_default(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 3
    assert all(t["type"] == "model" and t["enabled"] for t in data)
    repo_ids = {t["spec"]["repo_id"] for t in data}
    assert "mistralai/Mixtral-8x7B-Instruct-v0.1" in repo_ids


def test_create_model_template(client):
    resp = client.post("/api/templates", json=MODEL_PAYLOAD)
    assert resp.status_code == 201

    data = resp.json()
    assert data["type"] == "model"
    assert data["enabled"] is True
    assert data["spec"]["num_experts"] == 8
    assert "id" in data and "created_at" in data


def test_create_docker_registry_template(client):
    resp = client.post("/api/templates", json=DOCKER_PAYLOAD)
    assert resp.status_code == 201

    data = resp.json()
    assert data["type"] == "docker_registry"
    assert data["spec"]["image"] == "vllm/vllm-openai"
    assert data["spec"]["gpu_compatible"] == ["nvidia-ampere", "nvidia-hopper"]


def test_create_disabled_template(client):
    resp = client.post("/api/templates", json={**MODEL_PAYLOAD, "enabled": False})
    assert resp.status_code == 201
    assert resp.json()["enabled"] is False


def test_create_rejects_spec_type_mismatch(client):
    bad_payload = {**MODEL_PAYLOAD, "type": "docker_registry"}
    resp = client.post("/api/templates", json=bad_payload)
    assert resp.status_code == 422


def test_get_template_roundtrip(client):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()

    resp = client.get(f"/api/templates/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == created


def test_get_template_not_found(client):
    resp = client.get("/api/templates/does-not-exist")
    assert resp.status_code == 404


def test_list_templates_filters_by_type(client):
    client.post("/api/templates", json=MODEL_PAYLOAD)
    client.post("/api/templates", json=DOCKER_PAYLOAD)

    resp = client.get("/api/templates", params={"type": "docker_registry"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "docker_registry"


def test_list_templates_filters_by_enabled(client):
    client.post("/api/templates", json={**MODEL_PAYLOAD, "enabled": False})

    resp = client.get("/api/templates", params={"type": "model", "enabled": "false"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["enabled"] is False


def test_update_template(client):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()

    updated_payload = {**MODEL_PAYLOAD, "name": "Mixtral 8x22B (rinominato)"}
    resp = client.put(f"/api/templates/{created['id']}", json=updated_payload)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Mixtral 8x22B (rinominato)"
    assert resp.json()["id"] == created["id"]


def test_update_template_not_found(client):
    resp = client.put("/api/templates/does-not-exist", json=MODEL_PAYLOAD)
    assert resp.status_code == 404


def test_delete_template(client):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()

    resp = client.delete(f"/api/templates/{created['id']}")
    assert resp.status_code == 204

    assert client.get(f"/api/templates/{created['id']}").status_code == 404


def test_delete_template_not_found(client):
    resp = client.delete("/api/templates/does-not-exist")
    assert resp.status_code == 404


def _fake_spec(repo_id: str) -> ModelTemplateSpec:
    return ModelTemplateSpec(
        repo_id=repo_id,
        architecture="mixtral",
        num_experts=8,
        num_experts_active=2,
        num_layers=32,
        params_billion=46.7,
        shard_size_gb=9.3,
        num_shards=5,
        context_length=32768,
        quantization="bfloat16",
    )


def test_create_template_from_hf(client, monkeypatch):
    monkeypatch.setattr(hf_metadata_service, "fetch_model_metadata", lambda repo_id: _fake_spec(repo_id))

    resp = client.post(
        "/api/templates/from-hf",
        json={"repo_id": "mistralai/Mixtral-8x7B-Instruct-v0.1", "name": "Mixtral (da HF)"},
    )
    assert resp.status_code == 201

    data = resp.json()
    assert data["name"] == "Mixtral (da HF)"
    assert data["spec"]["repo_id"] == "mistralai/Mixtral-8x7B-Instruct-v0.1"
    assert data["spec"]["num_layers"] == 32


def test_create_template_from_hf_defaults_name_to_repo_id(client, monkeypatch):
    monkeypatch.setattr(hf_metadata_service, "fetch_model_metadata", lambda repo_id: _fake_spec(repo_id))

    resp = client.post("/api/templates/from-hf", json={"repo_id": "org/some-model"})
    assert resp.json()["name"] == "org/some-model"


def test_create_template_from_hf_propagates_error(client, monkeypatch):
    def _raise(repo_id: str):
        raise hf_metadata_service.HFMetadataError("repo introvabile")

    monkeypatch.setattr(hf_metadata_service, "fetch_model_metadata", _raise)

    resp = client.post("/api/templates/from-hf", json={"repo_id": "org/does-not-exist"})
    assert resp.status_code == 502


def test_sync_template_from_hf_updates_spec(client, monkeypatch):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()

    monkeypatch.setattr(hf_metadata_service, "fetch_model_metadata", lambda repo_id: _fake_spec(repo_id))

    resp = client.post(f"/api/templates/{created['id']}/sync-hf")
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == created["id"]
    assert data["name"] == created["name"]  # nome/descrizione/enabled non toccati dal sync
    assert data["spec"]["num_layers"] == 32
    assert data["spec"]["quantization"] == "bfloat16"


def test_sync_template_from_hf_not_found(client):
    resp = client.post("/api/templates/does-not-exist/sync-hf")
    assert resp.status_code == 404


def test_sync_template_from_hf_rejects_docker_template(client):
    created = client.post("/api/templates", json=DOCKER_PAYLOAD).json()

    resp = client.post(f"/api/templates/{created['id']}/sync-hf")
    assert resp.status_code == 400


def _mark_downloading(template: Template) -> Template:
    return template.model_copy(update={"spec": template.spec.model_copy(update={"library_status": LibraryStatus.DOWNLOADING})})


def test_download_to_library(client, monkeypatch):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()
    monkeypatch.setattr(model_library_service, "start_download", lambda t: _mark_downloading(t))

    resp = client.post(f"/api/templates/{created['id']}/library/download")
    assert resp.status_code == 200
    assert resp.json()["spec"]["library_status"] == "downloading"


def test_download_to_library_rejects_docker_template(client):
    created = client.post("/api/templates", json=DOCKER_PAYLOAD).json()

    resp = client.post(f"/api/templates/{created['id']}/library/download")
    assert resp.status_code == 400


def test_download_to_library_propagates_error(client, monkeypatch):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()

    def _raise(t):
        raise model_library_service.ModelLibraryError("Docker non raggiungibile")

    monkeypatch.setattr(model_library_service, "start_download", _raise)

    resp = client.post(f"/api/templates/{created['id']}/library/download")
    assert resp.status_code == 502


def test_get_library_status(client, monkeypatch):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()
    monkeypatch.setattr(model_library_service, "get_status", lambda t: t)

    resp = client.get(f"/api/templates/{created['id']}/library")
    assert resp.status_code == 200


def test_verify_library_endpoint(client, monkeypatch):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()
    monkeypatch.setattr(model_library_service, "verify_library", lambda t: t)

    resp = client.post(f"/api/templates/{created['id']}/library/verify")
    assert resp.status_code == 200


def test_delete_library_endpoint(client, monkeypatch):
    created = client.post("/api/templates", json=MODEL_PAYLOAD).json()
    monkeypatch.setattr(model_library_service, "delete_library", lambda t: t)

    resp = client.delete(f"/api/templates/{created['id']}/library")
    assert resp.status_code == 200
