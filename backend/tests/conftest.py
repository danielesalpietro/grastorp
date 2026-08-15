import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Ogni test scrive su un file SQLite temporaneo e isolato."""
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")


@pytest.fixture
def client():
    return TestClient(app)
