import httpx
import pytest

from app.schemas import ModelRegistry, RegistryProvider
from app.services import hf_metadata_service


def _registry(**overrides) -> ModelRegistry:
    return ModelRegistry(
        id="huggingface",
        name="Hugging Face",
        provider=RegistryProvider.HUGGINGFACE,
        base_url="https://huggingface.co",
        created_at="2024-01-01T00:00:00+00:00",
        **overrides,
    )


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_fetch_model_metadata_parses_config_and_safetensors(monkeypatch):
    def _fake_get(url, timeout, headers):
        if url.endswith("/tree/main"):
            return _FakeResponse(json_data=[{"path": "model-00001.safetensors", "size": 1_000_000_000}])
        return _FakeResponse(
            json_data={
                "config": {
                    "model_type": "mixtral",
                    "num_local_experts": 8,
                    "num_experts_per_tok": 2,
                    "num_hidden_layers": 32,
                    "max_position_embeddings": 32768,
                    "torch_dtype": "bfloat16",
                },
                "safetensors": {"total": 46_700_000_000},
            }
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    spec = hf_metadata_service.fetch_model_metadata(_registry(), "mistralai/Mixtral-8x7B-Instruct-v0.1")

    assert spec.architecture == "mixtral"
    assert spec.num_experts == 8
    assert spec.num_experts_active == 2
    assert spec.num_layers == 32
    assert spec.context_length == 32768
    assert spec.quantization == "bfloat16"
    assert spec.params_billion == 46.7
    assert spec.num_shards == 1
    assert spec.registry_id == "huggingface"


def test_fetch_model_metadata_sends_authorization_header_when_api_key_set(monkeypatch):
    captured = {}

    def _fake_get(url, timeout, headers):
        captured["headers"] = headers
        if url.endswith("/tree/main"):
            return _FakeResponse(json_data=[])
        return _FakeResponse(json_data={"config": {}, "safetensors": {}})

    monkeypatch.setattr(httpx, "get", _fake_get)
    hf_metadata_service.fetch_model_metadata(_registry(api_key="tok-123"), "org/model")

    assert captured["headers"]["Authorization"] == "Bearer tok-123"


def test_fetch_model_metadata_raises_on_404(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout, headers: _FakeResponse(status_code=404))

    with pytest.raises(hf_metadata_service.HFMetadataError):
        hf_metadata_service.fetch_model_metadata(_registry(), "org/does-not-exist")


def test_fetch_model_metadata_raises_on_network_error(monkeypatch):
    def _raise(url, timeout, headers):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "get", _raise)

    with pytest.raises(hf_metadata_service.HFMetadataError):
        hf_metadata_service.fetch_model_metadata(_registry(), "org/model")


def test_search_models_parses_results(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, timeout, headers: _FakeResponse(
            json_data=[
                {"id": "mistralai/Mixtral-8x7B-Instruct-v0.1", "downloads": 500, "likes": 10, "pipeline_tag": "text-generation"},
                {"modelId": "org/mixtral-clone", "downloads": 1},
                {"downloads": 2},  # senza id: scartato
            ]
        ),
    )

    results = hf_metadata_service.search_models(_registry(), "mixtral")

    assert [r["repo_id"] for r in results] == ["mistralai/Mixtral-8x7B-Instruct-v0.1", "org/mixtral-clone"]


def test_search_models_returns_empty_on_unexpected_response(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda url, timeout, headers: _FakeResponse(json_data={"not": "a list"}))

    assert hf_metadata_service.search_models(_registry(), "mixtral") == []
