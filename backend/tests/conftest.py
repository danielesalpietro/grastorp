import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


@pytest.fixture(autouse=True)
def _clear_store():
    store._deployments.clear()
    yield
    store._deployments.clear()


@pytest.fixture
def client():
    return TestClient(app)
