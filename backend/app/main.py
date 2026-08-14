from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import deployments, models, system
from app.services import docker_service

app = FastAPI(title="Grastorp", description="Hypervisor per Mixture-of-Experts")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deployments.router)
app.include_router(models.router)
app.include_router(system.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "docker": docker_service.docker_available()}
