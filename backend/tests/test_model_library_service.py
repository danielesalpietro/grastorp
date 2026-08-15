import json

import pytest
from docker.errors import NotFound

from app import datastore_store, library_config_store
from app.schemas import Datastore, DatastoreType, LibraryConfig, LibraryStatus, ModelTemplateSpec, Template, TemplateType
from app.services import hf_metadata_service, model_library_service


def _model_template(**spec_overrides) -> Template:
    spec = ModelTemplateSpec(
        repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
        architecture="mixtral",
        num_experts=8,
        **spec_overrides,
    )
    return Template(
        id="tpl-1",
        type=TemplateType.MODEL,
        name="Mixtral 8x7B Instruct",
        enabled=True,
        spec=spec,
        created_at="2024-01-01T00:00:00+00:00",
    )


class _FakeContainer:
    def __init__(self, status="running", exit_code=0, logs=b""):
        self.status = status
        self.exit_code = exit_code
        self._logs = logs
        self.removed = False

    def reload(self):
        pass

    @property
    def attrs(self):
        return {"State": {"ExitCode": self.exit_code}}

    def logs(self, tail=None):
        return self._logs

    def remove(self, force=False):
        self.removed = True

    def wait(self, timeout=None):
        return {"StatusCode": self.exit_code}


class _FakeContainers:
    def __init__(self):
        self._by_name = {}
        self.run_calls: list[dict] = []

    def get(self, name):
        if name not in self._by_name:
            raise NotFound("not found")
        return self._by_name[name]

    def run(self, image, **kwargs):
        self.run_calls.append(kwargs)
        container = _FakeContainer(status="running")
        name = kwargs.get("name")
        if name:
            self._by_name[name] = container
        return container


class _FakeVolume:
    def __init__(self, name, registry):
        self.name = name
        self._registry = registry

    def remove(self, force=False):
        self._registry.pop(self.name, None)


class _FakeVolumes:
    def __init__(self):
        self._names: dict[str, dict] = {}
        self.created: list[dict] = []

    def get(self, name):
        if name not in self._names:
            raise NotFound("not found")
        return _FakeVolume(name, self._names)

    def create(self, name, **kwargs):
        self._names[name] = kwargs
        self.created.append({"name": name, **kwargs})


class _FakeClient:
    def __init__(self):
        self.containers = _FakeContainers()
        self.volumes = _FakeVolumes()


@pytest.fixture
def fake_client(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(model_library_service, "_get_client", lambda: client)
    return client


def test_start_download_creates_shared_volume_and_launches_container(fake_client):
    template = _model_template()

    updated = model_library_service.start_download(template)

    assert updated.spec.library_status is LibraryStatus.DOWNLOADING
    assert updated.spec.library_progress_percent == 0.0
    assert model_library_service.LIBRARY_VOLUME_NAME in fake_client.volumes._names
    assert len(fake_client.containers.run_calls) == 1
    run_kwargs = fake_client.containers.run_calls[0]
    assert run_kwargs["environment"]["REPO_ID"] == template.spec.repo_id
    assert run_kwargs["volumes"] == {model_library_service.LIBRARY_VOLUME_NAME: {"bind": "/data", "mode": "rw"}}


def test_start_download_reuses_existing_shared_volume(fake_client):
    model_library_service.start_download(_model_template())
    second = _model_template()
    second.id = "tpl-2"

    model_library_service.start_download(second)

    assert len(fake_client.volumes.created) == 1  # creato una sola volta, riusato per il secondo modello


def test_start_download_creates_nfs_backed_volume_from_configured_datastore(fake_client):
    datastore_store.save_datastore(
        Datastore(
            id="ds-nfs",
            name="NAS",
            type=DatastoreType.NFS,
            nfs_server="10.0.0.5",
            nfs_export_path="/export/grastorp",
            nfs_options="rw,nfsvers=4",
            created_at="2024-01-01T00:00:00+00:00",
        )
    )
    library_config_store.save_config(LibraryConfig(datastore_id="ds-nfs"))

    model_library_service.start_download(_model_template())

    created = fake_client.volumes.created[0]
    assert created["driver"] == "local"
    assert created["driver_opts"]["type"] == "nfs"
    assert created["driver_opts"]["o"] == "addr=10.0.0.5,rw,nfsvers=4"
    assert created["driver_opts"]["device"] == ":/export/grastorp"


def test_start_download_idempotent_when_already_running(fake_client):
    template = _model_template()
    first = model_library_service.start_download(template)

    second = model_library_service.start_download(first)

    assert len(fake_client.containers.run_calls) == 1  # non rilanciato
    assert second.spec.library_status is LibraryStatus.DOWNLOADING


def test_get_status_updates_progress_while_running(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING)
    container = _FakeContainer(status="running", logs=json.dumps({"done": 3, "total": 10}).encode())
    fake_client.containers._by_name[model_library_service._downloader_container_name(template.id)] = container

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.DOWNLOADING
    assert updated.spec.library_progress_percent == 30.0


def test_get_status_marks_ready_on_successful_exit(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING)
    container = _FakeContainer(status="exited", exit_code=0)
    fake_client.containers._by_name[model_library_service._downloader_container_name(template.id)] = container

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.READY
    assert updated.spec.library_progress_percent == 100.0
    assert updated.spec.downloaded_at is not None
    assert container.removed is True


def test_get_status_marks_error_on_failed_exit(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING)
    logs = json.dumps({"error": "repo privato, accesso negato"}).encode()
    container = _FakeContainer(status="exited", exit_code=1, logs=logs)
    fake_client.containers._by_name[model_library_service._downloader_container_name(template.id)] = container

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.ERROR
    assert "accesso negato" in updated.spec.library_error


def test_get_status_marks_error_when_container_missing(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING)

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.ERROR
    assert "non trovato" in updated.spec.library_error


def test_get_status_noop_when_not_downloading(fake_client):
    template = _model_template(library_status=LibraryStatus.READY)

    updated = model_library_service.get_status(template)

    assert updated == template
    assert fake_client.containers.run_calls == []


def test_verify_library_scopes_search_to_repo_cache_folder(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.READY)
    monkeypatch.setattr(
        hf_metadata_service,
        "list_safetensor_files",
        lambda registry, repo_id: [{"path": "model-00001.safetensors", "size": 100}],
    )
    found = json.dumps([{"name": "model-00001.safetensors", "size": 100}]).encode()
    fake_client.containers.run = lambda image, **kwargs: _FakeContainer(status="exited", exit_code=0, logs=found)

    updated = model_library_service.verify_library(template)

    assert updated.spec.library_status is LibraryStatus.READY
    assert updated.spec.library_error is None


def test_verify_library_passes_expected_cache_folder_env(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.READY)
    monkeypatch.setattr(
        hf_metadata_service, "list_safetensor_files", lambda registry, repo_id: [{"path": "x.safetensors", "size": 1}]
    )
    captured = {}

    def _run(image, **kwargs):
        captured.update(kwargs)
        return _FakeContainer(status="exited", exit_code=0, logs=b"[]")

    fake_client.containers.run = _run
    model_library_service.verify_library(template)

    assert captured["environment"]["CACHE_FOLDER"] == "models--mistralai--Mixtral-8x7B-Instruct-v0.1"
    assert captured["volumes"] == {model_library_service.LIBRARY_VOLUME_NAME: {"bind": "/data", "mode": "ro"}}


def test_verify_library_marks_error_when_file_missing(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.READY)
    monkeypatch.setattr(
        hf_metadata_service,
        "list_safetensor_files",
        lambda registry, repo_id: [{"path": "model-00001.safetensors", "size": 100}],
    )
    fake_client.containers.run = lambda image, **kwargs: _FakeContainer(status="exited", exit_code=0, logs=b"[]")

    updated = model_library_service.verify_library(template)

    assert updated.spec.library_status is LibraryStatus.ERROR
    assert "mancanti" in updated.spec.library_error


def test_verify_library_raises_without_reference_data(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.READY)
    monkeypatch.setattr(hf_metadata_service, "list_safetensor_files", lambda registry, repo_id: [])

    with pytest.raises(model_library_service.ModelLibraryError):
        model_library_service.verify_library(template)


def test_verify_library_rejects_when_never_downloaded(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.NOT_DOWNLOADED)
    monkeypatch.setattr(
        hf_metadata_service, "list_safetensor_files", lambda registry, repo_id: [{"path": "x.safetensors", "size": 1}]
    )

    with pytest.raises(model_library_service.ModelLibraryError):
        model_library_service.verify_library(template)


def test_delete_library_removes_only_this_model_leaves_shared_volume(fake_client):
    model_library_service.start_download(_model_template())  # crea il volume condiviso
    template = _model_template(library_status=LibraryStatus.READY, library_progress_percent=100.0)

    captured = {}

    def _run(image, **kwargs):
        captured.update(kwargs)
        return _FakeContainer(status="exited", exit_code=0)

    fake_client.containers.run = _run
    updated = model_library_service.delete_library(template)

    assert updated.spec.library_status is LibraryStatus.NOT_DOWNLOADED
    assert captured["environment"]["CACHE_FOLDER"] == "models--mistralai--Mixtral-8x7B-Instruct-v0.1"
    assert captured["volumes"] == {model_library_service.LIBRARY_VOLUME_NAME: {"bind": "/data", "mode": "rw"}}
    assert model_library_service.LIBRARY_VOLUME_NAME in fake_client.volumes._names  # non rimosso
