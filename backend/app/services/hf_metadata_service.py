"""Recupero delle caratteristiche tecniche di un modello direttamente da Hugging Face Hub.

Dato un repo_id, interroga la REST API pubblica di HF Hub (config.json del modello
ed elenco dei file) per ricavare architettura, esperti, layer, parametri e sharding,
quando disponibili. I campi non ricavabili restano None: HF non garantisce la stessa
struttura di config.json per ogni architettura.
"""

from __future__ import annotations

import httpx

from app.schemas import ModelTemplateSpec

_HF_API_BASE = "https://huggingface.co/api/models"
_TIMEOUT = 10.0


class HFMetadataError(Exception):
    """Il repo non esiste, non è raggiungibile, o HF ha risposto con un errore."""


def _get_json(url: str) -> dict | list:
    try:
        resp = httpx.get(url, timeout=_TIMEOUT, headers={"User-Agent": "grastorp"})
    except httpx.HTTPError as exc:
        raise HFMetadataError(f"Impossibile contattare Hugging Face: {exc}") from exc
    if resp.status_code == 404:
        raise HFMetadataError(f"Repository non trovato su Hugging Face: {url}")
    if resp.status_code != 200:
        raise HFMetadataError(f"Hugging Face ha risposto {resp.status_code} per {url}")
    return resp.json()


def _first_int_field(config: dict, *names: str) -> int | None:
    for name in names:
        value = config.get(name)
        if isinstance(value, int):
            return value
    return None


def list_safetensor_files(repo_id: str) -> list[dict]:
    """Elenca i file .safetensors del repo (path e size in byte), per sharding e verifica integrità.

    Ritorna [] se il repo non ha file .safetensors o se l'elenco non è ottenibile:
    è un dato best-effort, chi lo consuma deve gestire la lista vuota.
    """
    try:
        files = _get_json(f"{_HF_API_BASE}/{repo_id}/tree/main")
    except HFMetadataError:
        return []

    if not isinstance(files, list):
        return []

    return [f for f in files if isinstance(f, dict) and str(f.get("path", "")).endswith(".safetensors")]


def _shard_info(repo_id: str, total_params: float | int | None) -> tuple[int | None, float | None]:
    """Conta i file .safetensors del repo per stimare numero e dimensione degli shard."""
    shard_files = list_safetensor_files(repo_id)
    if not shard_files:
        return None, None

    num_shards = len(shard_files)
    sizes = [f["size"] for f in shard_files if isinstance(f.get("size"), (int, float))]
    if sizes:
        shard_size_gb = round((sum(sizes) / len(sizes)) / 1e9, 2)
    elif total_params:
        # Nessuna dimensione file riportata da HF: stima approssimativa assumendo bf16 (2 byte/parametro).
        shard_size_gb = round((total_params * 2 / num_shards) / 1e9, 2)
    else:
        shard_size_gb = None

    return num_shards, shard_size_gb


def fetch_model_metadata(repo_id: str) -> ModelTemplateSpec:
    """Interroga HF Hub e costruisce uno ModelTemplateSpec best-effort per repo_id."""

    info = _get_json(f"{_HF_API_BASE}/{repo_id}?expand[]=config&expand[]=safetensors")
    if not isinstance(info, dict):
        raise HFMetadataError(f"Risposta inattesa da Hugging Face per {repo_id}")

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

    num_shards, shard_size_gb = _shard_info(repo_id, total_params)

    return ModelTemplateSpec(
        repo_id=repo_id,
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
