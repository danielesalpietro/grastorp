def test_list_models_returns_moe_catalog(client):
    resp = client.get("/api/models")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) >= 1
    assert all(m["architecture"] == "moe" for m in data)

    repo_ids = {m["repo_id"] for m in data}
    assert "mistralai/Mixtral-8x7B-Instruct-v0.1" in repo_ids
