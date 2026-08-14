"""Store in-memory dei deployment. Da sostituire con una persistenza reale (sqlite/postgres)."""

from __future__ import annotations

from app.schemas import Deployment

_deployments: dict[str, Deployment] = {}


def list_deployments() -> list[Deployment]:
    return list(_deployments.values())


def get_deployment(deployment_id: str) -> Deployment | None:
    return _deployments.get(deployment_id)


def save_deployment(deployment: Deployment) -> None:
    _deployments[deployment.id] = deployment


def delete_deployment(deployment_id: str) -> None:
    _deployments.pop(deployment_id, None)
