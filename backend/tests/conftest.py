import pytest
from fastapi.testclient import TestClient

from app import datastore_store, library_config_store, store, template_store
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Ogni test scrive su un file SQLite temporaneo e isolato."""
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")


@pytest.fixture(autouse=True)
def _isolate_template_store(tmp_path, monkeypatch):
    monkeypatch.setattr(template_store, "TEMPLATES_FILE", tmp_path / "templates.json")


@pytest.fixture(autouse=True)
def _isolate_datastore_store(tmp_path, monkeypatch):
    monkeypatch.setattr(datastore_store, "DATASTORES_FILE", tmp_path / "datastores.json")


@pytest.fixture(autouse=True)
def _isolate_library_config_store(tmp_path, monkeypatch):
    monkeypatch.setattr(library_config_store, "LIBRARY_CONFIG_FILE", tmp_path / "library_config.json")


@pytest.fixture
def client():
    return TestClient(app)
