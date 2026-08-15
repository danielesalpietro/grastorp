"""Recupero delle caratteristiche tecniche di un modello da un registry (Hugging Face Hub o
un endpoint compatibile, es. mirror aziendale self-hosted).

Dato un repo_id, interroga la REST API del registry (config.json del modello ed
elenco dei file) per ricavare architettura, esperti, layer, parametri e sharding,
quando disponibili. I campi non ricavabili restano None: HF non garantisce la stessa
struttura di config.json per ogni architettura. Espone anche una ricerca per nome,
usata per popolare la scelta del modello nel catalogo di un registry.
"""

from __future__ import annotations

import httpx

from app.schemas import ModelRegistry, ModelTemplateSpec

_TIMEOUT = 10.0


class HFMetadataError(Exception):
    """Il repo non esiste, non è raggiungibile, o il registry ha risposto con un errore."""


def _api_base(registry: ModelRegistry) -> str:
    return f"{registry.base_url.rstrip('/')}/api/models"


def _headers(registry: ModelRegistry) -> dict:
    headers = {"User-Agent": "grastorp"}
    if registry.api_key:
        headers["Authorization"] = f"Bearer {registry.api_key}"
    return headers


def _get_json(url: str, registry: ModelRegistry) -> dict | list:
    try:
        resp = httpx.get(url, timeout=_TIMEOUT, headers=_headers(registry))
    except httpx.HTTPError as exc:
        raise HFMetadataError(f"Impossibile contattare {registry.name}: {exc}") from exc
    if resp.status_code == 404:
        raise HFMetadataError(f"Repository non trovato su {registry.name}: {url}")
    if resp.status_code != 200:
        raise HFMetadataError(f"{registry.name} ha risposto {resp.status_code} per {url}")
    return resp.json()


def _first_int_field(config: dict, *names: str) -> int | None:
    for name in names:
        value = config.get(name)
        if isinstance(value, int):
            return value
    return None


def search_models(registry: ModelRegistry, query: str, limit: int = 20) -> list[dict]:
    """Cerca modelli per nome/parola chiave nel registry (es. 'mixtral')."""
    results = _get_json(f"{_api_base(registry)}?search={query}&limit={limit}", registry)
    if not isinstance(results, list):
        return []
    return [
        {
            "repo_id": r.get("id") or r.get("modelId"),
            "downloads": r.get("downloads"),
            "likes": r.get("likes"),
            "pipeline_tag": r.get("pipeline_tag"),
        }
        for r in results
        if isinstance(r, dict) and (r.get("id") or r.get("modelId"))
    ]


def list_safetensor_files(registry: ModelRegistry, repo_id: str) -> list[dict]:
    """Elenca i file .safetensors del repo (path e size in byte), per sharding e verifica integrità.

    Ritorna [] se il repo non ha file .safetensors o se l'elenco non è ottenibile:
    è un dato best-effort, chi lo consuma deve gestire la lista vuota.
    """
    try:
        files = _get_json(f"{_api_base(registry)}/{repo_id}/tree/main", registry)
    except HFMetadataError:
        return []

    if not isinstance(files, list):
        return []

    return [f for f in files if isinstance(f, dict) and str(f.get("path", "")).endswith(".safetensors")]


def _shard_info(registry: ModelRegistry, repo_id: str, total_params: float | int | None) -> tuple[int | None, float | None]:
    """Conta i file .safetensors del repo per stimare numero e dimensione degli shard."""
    shard_files = list_safetensor_files(registry, repo_id)
    if not shard_files:
        return None, None

    num_shards = len(shard_files)
    sizes = [f["size"] for f in shard_files if isinstance(f.get("size"), (int, float))]
    if sizes:
        shard_size_gb = round((sum(sizes) / len(sizes)) / 1e9, 2)
    elif total_params:
        # Nessuna dimensione file riportata dal registry: stima approssimativa assumendo bf16 (2 byte/parametro).
        shard_size_gb = round((total_params * 2 / num_shards) / 1e9, 2)
    else:
        shard_size_gb = None

    return num_shards, shard_size_gb


def fetch_model_metadata(registry: ModelRegistry, repo_id: str) -> ModelTemplateSpec:
    """Interroga il registry e costruisce uno ModelTemplateSpec best-effort per repo_id."""

    info = _get_json(f"{_api_base(registry)}/{repo_id}?expand[]=config&expand[]=safetensors", registry)
    if not isinstance(info, dict):
        raise HFMetadataError(f"Risposta inattesa da {registry.name} per {repo_id}")

    config = info.get("config") or {}

    architecture = config.get("model_type") or info.get("pipeline_tag") or "unknown"
    num_experts = _first_int_field(config, "num_local_experts", "n_routed_experts", "num_experts")
    num_experts_active = _first_int_field(config, "num_experts_per_tok", "num_experts_per_token")
    num_layers = _first_int_field(config, "num_hidden_layers", "n_layer")
    context_length = _first_int_field(config, "max_position_embeddings")
    quantization = config.get("torch_dtype")

    safetensors = info.get("safetensors") or {}
    total_params = safetensors.get("total")
    params_billion = round(total_params / 1e9, 2) if isinstance(total_params, (int, float)) else None

    num_shards, shard_size_gb = _shard_info(registry, repo_id, total_params)

    return ModelTemplateSpec(
        repo_id=repo_id,
        registry_id=registry.id,
        architecture=architecture,
        num_experts=num_experts,
        num_experts_active=num_experts_active,
        num_layers=num_layers,
        params_billion=params_billion,
        shard_size_gb=shard_size_gb,
        num_shards=num_shards,
        context_length=context_length,
        quantization=quantization,
    )
