import pytest
from fastapi.testclient import TestClient

from app import store, template_store
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Ogni test scrive su un file SQLite temporaneo e isolato."""
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")


@pytest.fixture(autouse=True)
def _isolate_template_store(tmp_path, monkeypatch):
    monkeypatch.setattr(template_store, "TEMPLATES_FILE", tmp_path / "templates.json")


@pytest.fixture
def client():
    return TestClient(app)
