"""Catalogo modelli Hugging Face disponibili per il deploy.

Stub: elenco statico dei soli modelli Mixture-of-Experts supportati.
In futuro andrà sostituito con una query reale all'HF Hub API
(https://huggingface.co/api/models?filter=...), filtrando per architettura MoE
e compatibilità col framework scelto.
"""

from __future__ import annotations

from app.schemas import HFModel, ModelArchitecture

_MOE_CATALOG: list[HFModel] = [
    HFModel(
        repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
        display_name="Mixtral 8x7B Instruct",
        architecture=ModelArchitecture.MIXTURE_OF_EXPERTS,
        num_experts=8,
        params_billion=46.7,
        description="Mixture-of-Experts di Mistral AI, 8 esperti da 7B, 2 attivi per token.",
    ),
    HFModel(
        repo_id="mistralai/Mixtral-8x22B-Instruct-v0.1",
        display_name="Mixtral 8x22B Instruct",
        architecture=ModelArchitecture.MIXTURE_OF_EXPERTS,
        num_experts=8,
        params_billion=141.0,
        description="Variante Mixtral su larga scala, 8 esperti da 22B.",
    ),
    HFModel(
        repo_id="deepseek-ai/deepseek-moe-16b-chat",
        display_name="DeepSeek-MoE 16B Chat",
        architecture=ModelArchitecture.MIXTURE_OF_EXPERTS,
        num_experts=64,
        params_billion=16.4,
        description="MoE fine-grained di DeepSeek con routing su 64 esperti.",
    ),
]


def list_moe_models() -> list[HFModel]:
    return list(_MOE_CATALOG)


def get_model(repo_id: str) -> HFModel | None:
    return next((m for m in _MOE_CATALOG if m.repo_id == repo_id), None)
