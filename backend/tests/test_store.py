import sqlite3

from app import store
from app.schemas import (
    Deployment,
    DeploymentState,
    NetworkConfig,
    ResourceConfig,
)


def _deployment(deployment_id: str) -> Deployment:
    return Deployment(
        id=deployment_id,
        name="test",
        model_repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
        framework="vllm",
        webui="none",
        resources=ResourceConfig(),
        network=NetworkConfig(api_port=8000),
        state=DeploymentState.STOPPED,
        created_at="2026-01-01T00:00:00Z",
    )


def test_save_and_get_roundtrip():
    deployment = _deployment("dep-1")
    store.save_deployment(deployment)

    fetched = store.get_deployment("dep-1")
    assert fetched == deployment


def test_save_upserts_existing_id():
    deployment = _deployment("dep-1")
    store.save_deployment(deployment)

    deployment.state = DeploymentState.RUNNING
    deployment.container_id = "abc123"
    store.save_deployment(deployment)

    fetched = store.get_deployment("dep-1")
    assert fetched.state == DeploymentState.RUNNING
    assert fetched.container_id == "abc123"
    assert len(store.list_deployments()) == 1


def test_delete_removes_deployment():
    store.save_deployment(_deployment("dep-1"))
    store.delete_deployment("dep-1")
    assert store.get_deployment("dep-1") is None
    assert store.list_deployments() == []


def test_data_is_actually_written_to_disk(monkeypatch, tmp_path):
    """Regressione: i dati devono finire su file, non restare in un dict in
    memoria nel modulo (com'era prima di introdurre SQLite)."""
    db_path = tmp_path / "persist.db"
    monkeypatch.setattr(store, "DB_PATH", db_path)

    store.save_deployment(_deployment("dep-1"))

    assert db_path.exists()

    # letta con una connessione sqlite3 indipendente, non tramite il modulo store
    raw_conn = sqlite3.connect(db_path)
    row = raw_conn.execute("SELECT id FROM deployments WHERE id = ?", ("dep-1",)).fetchone()
    raw_conn.close()

    assert row == ("dep-1",)
