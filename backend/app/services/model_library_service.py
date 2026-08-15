"""Library condivisa dei pesi dei modelli: un volume Docker per repo_id, scaricato una
sola volta e montato in sola lettura dai deployment che lo usano.

Il backend gira containerizzato con solo il socket Docker montato (vedi
docker_service.py e docker-compose.yml): non ha accesso diretto al filesystem
dell'host, quindi non può scrivere lui stesso dentro un volume. Il download
avviene perciò in un container "helper" (sibling, avviato via socket, stesso
pattern usato per vLLM), che il backend orchestra e monitora tramite l'API
Docker (stato del container + log) senza mai montare il volume su se stesso.

Il download usa huggingface_hub, la stessa libreria che vLLM userebbe per
scaricare il modello da sé: la cache che scrive nel volume (cartelle
models--org--name/, file .incomplete per i download interrotti) è la stessa
struttura, quindi riprende da dove si era fermato in modo nativo, senza
logica di resume custom.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import docker
from docker.errors import DockerException, NotFound

from app import template_store
from app.schemas import LibraryStatus, ModelTemplateSpec, Template, TemplateType
from app.services import hf_metadata_service

_DOWNLOADER_IMAGE = "python:3.11-slim"
_MOUNT_PATH = "/data"

# pip install ad ogni avvio: evita di dover costruire/pubblicare un'immagine
# dedicata per ora. Da sostituire con un'immagine pre-costruita se il costo
# (pochi secondi, trascurabile rispetto al download) diventa un problema.
_DOWNLOAD_SCRIPT = """
import json, os, sys
pip_status = os.system("pip install --quiet --no-cache-dir huggingface_hub==0.24.6")
if pip_status != 0:
    print(json.dumps({"error": "impossibile installare huggingface_hub"}), flush=True)
    sys.exit(1)
from huggingface_hub import HfApi, hf_hub_download

repo_id = os.environ["REPO_ID"]
try:
    api = HfApi()
    info = api.model_info(repo_id)
    keep = (".safetensors", ".json", ".model", ".txt")
    files = [f.rfilename for f in info.siblings if f.rfilename.endswith(keep) or f.rfilename.startswith("tokenizer")]
    total = len(files)
    for i, filename in enumerate(files, start=1):
        hf_hub_download(repo_id=repo_id, filename=filename, cache_dir="/data")
        print(json.dumps({"done": i, "total": total}), flush=True)
except Exception as exc:
    print(json.dumps({"error": str(exc)}), flush=True)
    sys.exit(1)
"""

_VERIFY_SCRIPT = """
import json, os

result = []
for root, _dirs, filenames in os.walk("/data"):
    for name in filenames:
        if name.endswith(".safetensors"):
            result.append({"name": name, "size": os.path.getsize(os.path.join(root, name))})
print(json.dumps(result))
"""

_client: docker.DockerClient | None = None


class ModelLibraryError(Exception):
    """Operazione sulla Library non eseguibile (repo non valido, dati mancanti, Docker irraggiungibile)."""


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def _volume_name(repo_id: str) -> str:
    slug = re.sub(r"[^a-z0-9_.-]+", "-", repo_id.lower()).strip("-")
    return f"grastorp-model-{slug}"


def _downloader_container_name(template_id: str) -> str:
    return f"grastorp-dl-{template_id}"


def _find_container(client: docker.DockerClient, name: str):
    try:
        return client.containers.get(name)
    except NotFound:
        return None


def _model_spec(template: Template) -> ModelTemplateSpec:
    if template.type is not TemplateType.MODEL or not isinstance(template.spec, ModelTemplateSpec):
        raise ModelLibraryError("La Library è disponibile solo per i template modello")
    return template.spec


def _last_json_line(logs: bytes) -> dict | None:
    for line in reversed(logs.decode(errors="replace").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def start_download(template: Template) -> Template:
    """Avvia (o riprende) il download dei pesi nel volume dedicato al repo."""
    spec = _model_spec(template)

    try:
        client = _get_client()
    except DockerException as exc:
        raise ModelLibraryError(f"Docker non raggiungibile: {exc}") from exc

    volume_name = spec.volume_name or _volume_name(spec.repo_id)
    try:
        client.volumes.get(volume_name)
    except NotFound:
        client.volumes.create(name=volume_name)

    container_name = _downloader_container_name(template.id)
    existing = _find_container(client, container_name)
    already_running = existing is not None and existing.status == "running"

    if existing is not None and not already_running:
        existing.remove(force=True)

    if not already_running:
        client.containers.run(
            _DOWNLOADER_IMAGE,
            command=["python3", "-c", _DOWNLOAD_SCRIPT],
            name=container_name,
            detach=True,
            volumes={volume_name: {"bind": _MOUNT_PATH, "mode": "rw"}},
            environment={"REPO_ID": spec.repo_id},
        )

    updated_spec = spec.model_copy(
        update={
            "volume_name": volume_name,
            "library_status": LibraryStatus.DOWNLOADING,
            "library_error": None,
            "library_progress_percent": spec.library_progress_percent if already_running else 0.0,
        }
    )
    return _persist(template, updated_spec)


def get_status(template: Template) -> Template:
    """Riallinea lo stato salvato con quello reale del container di download, se in corso."""
    spec = _model_spec(template)
    if spec.library_status is not LibraryStatus.DOWNLOADING:
        return template

    try:
        client = _get_client()
    except DockerException as exc:
        raise ModelLibraryError(f"Docker non raggiungibile: {exc}") from exc

    container = _find_container(client, _downloader_container_name(template.id))
    if container is None:
        updated_spec = spec.model_copy(
            update={"library_status": LibraryStatus.ERROR, "library_error": "Container di download non trovato"}
        )
        return _persist(template, updated_spec)

    container.reload()
    if container.status == "running":
        progress = _last_json_line(container.logs(tail=20))
        percent = spec.library_progress_percent
        if progress and progress.get("total"):
            percent = round(100 * progress["done"] / progress["total"], 1)
        updated_spec = spec.model_copy(update={"library_progress_percent": percent})
        return _persist(template, updated_spec)

    exit_code = container.attrs.get("State", {}).get("ExitCode", 1)
    last_line = _last_json_line(container.logs(tail=20))
    container.remove(force=True)

    if exit_code == 0:
        updated_spec = spec.model_copy(
            update={
                "library_status": LibraryStatus.READY,
                "library_progress_percent": 100.0,
                "library_error": None,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    else:
        error = (last_line or {}).get("error", "Download fallito (dettagli nei log del container)")
        updated_spec = spec.model_copy(update={"library_status": LibraryStatus.ERROR, "library_error": error})

    return _persist(template, updated_spec)


def verify_library(template: Template) -> Template:
    """Verifica che i file .safetensors nel volume corrispondano (nome e size) a quelli attesi da HF."""
    spec = _model_spec(template)
    if not spec.volume_name:
        raise ModelLibraryError("Nessun download in corso o completato per questo template")

    expected = hf_metadata_service.list_safetensor_files(spec.repo_id)
    if not expected:
        raise ModelLibraryError("Impossibile ottenere l'elenco file di riferimento da Hugging Face per la verifica")
    expected_by_name = {f["path"].rsplit("/", 1)[-1]: f.get("size") for f in expected}

    try:
        client = _get_client()
    except DockerException as exc:
        raise ModelLibraryError(f"Docker non raggiungibile: {exc}") from exc

    container = client.containers.run(
        _DOWNLOADER_IMAGE,
        command=["python3", "-c", _VERIFY_SCRIPT],
        detach=True,
        volumes={spec.volume_name: {"bind": _MOUNT_PATH, "mode": "ro"}},
    )
    try:
        container.wait(timeout=60)
        found = json.loads(container.logs().decode(errors="replace").strip().splitlines()[-1])
    finally:
        container.remove(force=True)

    found_by_name = {f["name"]: f["size"] for f in found}
    missing = [name for name in expected_by_name if name not in found_by_name]
    mismatched = [
        name
        for name, size in expected_by_name.items()
        if name in found_by_name and size is not None and found_by_name[name] != size
    ]

    if missing or mismatched:
        details = []
        if missing:
            details.append(f"mancanti: {', '.join(missing)}")
        if mismatched:
            details.append(f"dimensione errata: {', '.join(mismatched)}")
        updated_spec = spec.model_copy(
            update={"library_status": LibraryStatus.ERROR, "library_error": "Verifica integrità fallita: " + "; ".join(details)}
        )
    else:
        updated_spec = spec.model_copy(update={"library_status": LibraryStatus.READY, "library_error": None})

    return _persist(template, updated_spec)


def delete_library(template: Template) -> Template:
    """Rimuove il volume e resetta lo stato Library del template."""
    spec = _model_spec(template)

    try:
        client = _get_client()
    except DockerException as exc:
        raise ModelLibraryError(f"Docker non raggiungibile: {exc}") from exc

    container = _find_container(client, _downloader_container_name(template.id))
    if container is not None:
        container.remove(force=True)

    if spec.volume_name:
        try:
            client.volumes.get(spec.volume_name).remove(force=True)
        except NotFound:
            pass

    updated_spec = spec.model_copy(
        update={
            "volume_name": None,
            "library_status": LibraryStatus.NOT_DOWNLOADED,
            "library_progress_percent": None,
            "library_error": None,
            "downloaded_at": None,
        }
    )
    return _persist(template, updated_spec)


def _persist(template: Template, spec: ModelTemplateSpec) -> Template:
    updated = template.model_copy(update={"spec": spec})
    template_store.save_template(updated)
    return updated
