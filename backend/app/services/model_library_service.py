"""Model Library condivisa: un unico volume Docker per tutti i modelli, scaricati una
sola volta e montati in sola lettura dai deployment che li usano.

Il volume risiede sul datastore configurato (library_config_store + datastore_store):
locale (driver Docker di default) o su un mount NFS (driver_opts nativi del driver
'local' di Docker, nessun plugin di terze parti). All'interno, i modelli convivono
come sottocartelle: usiamo per il download la stessa struttura di cache che
huggingface_hub adotterebbe da sé (models--org--name/), quindi non serve gestire
manualmente il layout — e un download interrotto riprende da dove si era fermato
in modo nativo, senza logica di resume custom.

Il backend gira containerizzato con solo il socket Docker montato (vedi
docker_service.py e docker-compose.yml): non ha accesso diretto al filesystem
dell'host, quindi non può scrivere lui stesso dentro il volume. Ogni operazione
(download, verifica, rimozione di un singolo modello) avviene perciò in un
container "helper" (sibling, avviato via socket, stesso pattern usato per vLLM),
che il backend orchestra e monitora tramite l'API Docker (stato + log) senza mai
montare il volume su se stesso.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import docker
from docker.errors import DockerException, NotFound

from app import datastore_store, library_config_store, registry_store, template_store
from app.schemas import DatastoreType, LibraryStatus, ModelTemplateSpec, Template, TemplateType
from app.services import hf_metadata_service

LIBRARY_VOLUME_NAME = "grastorp-library"

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

base = os.path.join("/data", os.environ["CACHE_FOLDER"])
result = []
for root, _dirs, filenames in os.walk(base):
    for name in filenames:
        if name.endswith(".safetensors"):
            result.append({"name": name, "size": os.path.getsize(os.path.join(root, name))})
print(json.dumps(result))
"""

_DELETE_SCRIPT = """
import os, shutil
target = os.path.join("/data", os.environ["CACHE_FOLDER"])
if os.path.isdir(target):
    shutil.rmtree(target)
print("ok")
"""

_client: docker.DockerClient | None = None


class ModelLibraryError(Exception):
    """Operazione sulla Library non eseguibile (repo non valido, dati mancanti, Docker irraggiungibile)."""


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def _cache_folder(repo_id: str) -> str:
    """Nome della sottocartella che huggingface_hub userebbe per questo repo nella cache."""
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "--", repo_id)
    return f"models--{slug}"


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


def _ensure_library_volume(client: docker.DockerClient) -> None:
    """Crea il volume Library se non esiste, sul datastore attualmente configurato."""
    try:
        client.volumes.get(LIBRARY_VOLUME_NAME)
        return
    except NotFound:
        pass

    datastore_id = library_config_store.get_config().datastore_id
    datastore = datastore_store.get_datastore(datastore_id)
    if datastore is None:
        raise ModelLibraryError(f"Datastore '{datastore_id}' configurato per la Library non trovato")

    if datastore.type is DatastoreType.LOCAL:
        client.volumes.create(name=LIBRARY_VOLUME_NAME)
    elif datastore.type is DatastoreType.NFS:
        client.volumes.create(
            name=LIBRARY_VOLUME_NAME,
            driver="local",
            driver_opts={
                "type": "nfs",
                "o": f"addr={datastore.nfs_server},{datastore.nfs_options}",
                "device": f":{datastore.nfs_export_path}",
            },
        )
    else:
        raise ModelLibraryError(f"Datastore di tipo '{datastore.type.value}' non ancora supportato per la Library")


def start_download(template: Template) -> Template:
    """Avvia (o riprende) il download dei pesi nella Library condivisa."""
    spec = _model_spec(template)

    try:
        client = _get_client()
    except DockerException as exc:
        raise ModelLibraryError(f"Docker non raggiungibile: {exc}") from exc

    _ensure_library_volume(client)

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
            volumes={LIBRARY_VOLUME_NAME: {"bind": _MOUNT_PATH, "mode": "rw"}},
            environment={"REPO_ID": spec.repo_id},
        )

    updated_spec = spec.model_copy(
        update={
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
    """Verifica che i file .safetensors del modello nella Library corrispondano (nome e size) a quelli attesi dal registry."""
    spec = _model_spec(template)
    if spec.library_status is LibraryStatus.NOT_DOWNLOADED:
        raise ModelLibraryError("Nessun download in corso o completato per questo template")

    registry = registry_store.get_registry(spec.registry_id)
    if registry is None:
        raise ModelLibraryError(f"Registry '{spec.registry_id}' non trovato")

    expected = hf_metadata_service.list_safetensor_files(registry, spec.repo_id)
    if not expected:
        raise ModelLibraryError(f"Impossibile ottenere l'elenco file di riferimento da {registry.name} per la verifica")
    expected_by_name = {f["path"].rsplit("/", 1)[-1]: f.get("size") for f in expected}

    try:
        client = _get_client()
    except DockerException as exc:
        raise ModelLibraryError(f"Docker non raggiungibile: {exc}") from exc

    cache_folder = _cache_folder(spec.repo_id)
    container = client.containers.run(
        _DOWNLOADER_IMAGE,
        command=["python3", "-c", _VERIFY_SCRIPT],
        detach=True,
        volumes={LIBRARY_VOLUME_NAME: {"bind": _MOUNT_PATH, "mode": "ro"}},
        environment={"CACHE_FOLDER": cache_folder},
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
    """Rimuove solo i file di questo modello dalla Library (non tocca gli altri modelli nel volume condiviso)."""
    spec = _model_spec(template)

    try:
        client = _get_client()
    except DockerException as exc:
        raise ModelLibraryError(f"Docker non raggiungibile: {exc}") from exc

    downloader = _find_container(client, _downloader_container_name(template.id))
    if downloader is not None:
        downloader.remove(force=True)

    try:
        client.volumes.get(LIBRARY_VOLUME_NAME)
    except NotFound:
        pass
    else:
        container = client.containers.run(
            _DOWNLOADER_IMAGE,
            command=["python3", "-c", _DELETE_SCRIPT],
            detach=True,
            volumes={LIBRARY_VOLUME_NAME: {"bind": _MOUNT_PATH, "mode": "rw"}},
            environment={"CACHE_FOLDER": _cache_folder(spec.repo_id)},
        )
        try:
            container.wait(timeout=60)
        finally:
            container.remove(force=True)

    updated_spec = spec.model_copy(
        update={
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
