from fastapi import APIRouter

from app.schemas import HFModel
from app.services import hf_service

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[HFModel])
def list_models() -> list[HFModel]:
    """Elenco dei modelli MoE disponibili per il deploy (stub: catalogo statico)."""
    return hf_service.list_moe_models()
