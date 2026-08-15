from app.services import hf_metadata_service


def test_list_registries_seeded_with_huggingface_by_default(client):
    resp = client.get("/api/registries")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "huggingface"
    assert data[0]["enabled"] is True


def test_create_custom_registry(client):
    resp = client.post(
        "/api/registries",
        json={"name": "Mirror aziendale", "provider": "custom", "base_url": "https://hf.internal.example"},
    )
    assert resp.status_code == 201

    data = resp.json()
    assert data["provider"] == "custom"
    assert data["base_url"] == "https://hf.internal.example"


def test_create_custom_registry_requires_base_url(client):
    resp = client.post("/api/registries", json={"name": "Senza URL", "provider": "custom"})
    assert resp.status_code == 422


def test_create_registry_with_api_key(client):
    resp = client.post(
        "/api/registries",
        json={"name": "Mirror privato", "provider": "custom", "base_url": "https://x.example", "api_key": "secret"},
    )
    assert resp.status_code == 201
    assert resp.json()["api_key"] == "secret"


def test_get_registry_not_found(client):
    resp = client.get("/api/registries/does-not-exist")
    assert resp.status_code == 404


def test_update_registry(client):
    created = client.post(
        "/api/registries", json={"name": "Mirror", "provider": "custom", "base_url": "https://x.example"}
    ).json()

    resp = client.put(
        f"/api/registries/{created['id']}",
        json={"name": "Mirror rinominato", "provider": "custom", "base_url": "https://x.example", "enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Mirror rinominato"
    assert resp.json()["enabled"] is False


def test_delete_registry(client):
    created = client.post(
        "/api/registries", json={"name": "Mirror", "provider": "custom", "base_url": "https://x.example"}
    ).json()

    resp = client.delete(f"/api/registries/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/registries/{created['id']}").status_code == 404


def test_huggingface_registry_cannot_be_disabled(client):
    resp = client.put(
        "/api/registries/huggingface",
        json={"name": "Hugging Face", "provider": "huggingface", "base_url": "https://huggingface.co", "enabled": False},
    )
    assert resp.status_code == 409


def test_huggingface_registry_cannot_be_deleted(client):
    resp = client.delete("/api/registries/huggingface")
    assert resp.status_code == 409


def test_search_registry_models(client, monkeypatch):
    monkeypatch.setattr(
        hf_metadata_service,
        "search_models",
        lambda registry, query, limit=20: [{"repo_id": "mistralai/Mixtral-8x7B-Instruct-v0.1", "downloads": 100}],
    )

    resp = client.get("/api/registries/huggingface/search", params={"q": "mixtral"})
    assert resp.status_code == 200
    assert resp.json()[0]["repo_id"] == "mistralai/Mixtral-8x7B-Instruct-v0.1"


def test_search_registry_models_not_found(client):
    resp = client.get("/api/registries/does-not-exist/search", params={"q": "mixtral"})
    assert resp.status_code == 404


def test_search_registry_models_disabled(client):
    created = client.post(
        "/api/registries", json={"name": "Mirror", "provider": "custom", "base_url": "https://x.example"}
    ).json()
    client.put(
        f"/api/registries/{created['id']}",
        json={"name": "Mirror", "provider": "custom", "base_url": "https://x.example", "enabled": False},
    )

    resp = client.get(f"/api/registries/{created['id']}/search", params={"q": "mixtral"})
    assert resp.status_code == 400


def test_search_registry_models_propagates_error(client, monkeypatch):
    def _raise(registry, query, limit=20):
        raise hf_metadata_service.HFMetadataError("irraggiungibile")

    monkeypatch.setattr(hf_metadata_service, "search_models", _raise)

    resp = client.get("/api/registries/huggingface/search", params={"q": "mixtral"})
    assert resp.status_code == 502
