MODEL_PAYLOAD = {
    "type": "model",
    "name": "Mixtral 8x22B",
    "description": "MoE su larga scala",
    "spec": {
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


def test_list_templates_empty_by_default(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_model_template(client):
    resp = client.post("/api/templates", json=MODEL_PAYLOAD)
    assert resp.status_code == 201

    data = resp.json()
    assert data["type"] == "model"
    assert data["spec"]["num_experts"] == 8
    assert "id" in data and "created_at" in data


def test_create_docker_registry_template(client):
    resp = client.post("/api/templates", json=DOCKER_PAYLOAD)
    assert resp.status_code == 201

    data = resp.json()
    assert data["type"] == "docker_registry"
    assert data["spec"]["image"] == "vllm/vllm-openai"
    assert data["spec"]["gpu_compatible"] == ["nvidia-ampere", "nvidia-hopper"]


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
