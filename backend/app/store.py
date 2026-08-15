"""Persistenza dei deployment su SQLite.

Ogni deployment è salvato come riga con il JSON del modello Pydantic in una
colonna: evita di mantenere uno schema SQL parallelo (e le relative
migrazioni) mentre ResourceConfig/NetworkConfig sono ancora in evoluzione.
SQLite dà comunque scritture atomiche e un singolo file di database, adatto
a un volume Docker, a differenza di scrivere JSON su disco a mano.

Una connessione per operazione: le route sono handler sync, che FastAPI
esegue in un threadpool, quindi connessioni sqlite3 condivise tra thread
andrebbero gestite con cura. Aprire/chiudere per ogni chiamata evita il
problema, ed è sufficiente per i volumi in gioco qui.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from app.schemas import Deployment

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "grastorp.db"
DB_PATH = Path(os.environ.get("GRASTORP_DB_PATH", DEFAULT_DB_PATH))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS deployments (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def list_deployments() -> list[Deployment]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT data FROM deployments ORDER BY created_at").fetchall()
    finally:
        conn.close()
    return [Deployment.model_validate_json(row[0]) for row in rows]


def get_deployment(deployment_id: str) -> Deployment | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT data FROM deployments WHERE id = ?", (deployment_id,)
        ).fetchone()
    finally:
        conn.close()
    return Deployment.model_validate_json(row[0]) if row else None


def save_deployment(deployment: Deployment) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO deployments (id, data, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (deployment.id, deployment.model_dump_json(), deployment.created_at),
        )
        conn.commit()
    finally:
        conn.close()


def delete_deployment(deployment_id: str) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM deployments WHERE id = ?", (deployment_id,))
        conn.commit()
    finally:
        conn.close()
