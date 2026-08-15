def test_list_datastores_seeded_with_local_by_default(client):
    resp = client.get("/api/storage/datastores")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "local"
    assert data[0]["type"] == "local"


def test_create_nfs_datastore(client):
    resp = client.post(
        "/api/storage/datastores",
        json={
            "name": "NAS",
            "type": "nfs",
            "nfs_server": "10.0.0.5",
            "nfs_export_path": "/export/grastorp",
        },
    )
    assert resp.status_code == 201

    data = resp.json()
    assert data["type"] == "nfs"
    assert data["nfs_server"] == "10.0.0.5"


def test_create_nfs_datastore_requires_server_and_export(client):
    resp = client.post("/api/storage/datastores", json={"name": "NAS", "type": "nfs"})
    assert resp.status_code == 422


def test_create_iscsi_datastore_rejected(client):
    resp = client.post("/api/storage/datastores", json={"name": "SAN", "type": "iscsi"})
    assert resp.status_code == 422


def test_get_datastore_not_found(client):
    resp = client.get("/api/storage/datastores/does-not-exist")
    assert resp.status_code == 404


def test_delete_datastore(client):
    created = client.post(
        "/api/storage/datastores",
        json={"name": "NAS", "type": "nfs", "nfs_server": "10.0.0.5", "nfs_export_path": "/export"},
    ).json()

    resp = client.delete(f"/api/storage/datastores/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/storage/datastores/{created['id']}").status_code == 404


def test_delete_datastore_not_found(client):
    resp = client.delete("/api/storage/datastores/does-not-exist")
    assert resp.status_code == 404


def test_delete_datastore_in_use_by_library_is_blocked(client):
    resp = client.delete("/api/storage/datastores/local")  # è il default della Library
    assert resp.status_code == 409


def test_get_library_config_defaults_to_local(client):
    resp = client.get("/api/storage/library/config")
    assert resp.status_code == 200
    assert resp.json()["datastore_id"] == "local"


def test_set_library_config(client):
    created = client.post(
        "/api/storage/datastores",
        json={"name": "NAS", "type": "nfs", "nfs_server": "10.0.0.5", "nfs_export_path": "/export"},
    ).json()

    resp = client.put("/api/storage/library/config", json={"datastore_id": created["id"]})
    assert resp.status_code == 200
    assert resp.json()["datastore_id"] == created["id"]

    assert client.get("/api/storage/library/config").json()["datastore_id"] == created["id"]


def test_set_library_config_rejects_unknown_datastore(client):
    resp = client.put("/api/storage/library/config", json={"datastore_id": "does-not-exist"})
    assert resp.status_code == 400
