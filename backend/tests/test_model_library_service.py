import json

import pytest
from docker.errors import NotFound

from app.schemas import LibraryStatus, ModelTemplateSpec, Template, TemplateType
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
        self._registry.discard(self.name)


class _FakeVolumes:
    def __init__(self):
        self._names: set[str] = set()
        self.created: list[str] = []

    def get(self, name):
        if name not in self._names:
            raise NotFound("not found")
        return _FakeVolume(name, self._names)

    def create(self, name):
        self._names.add(name)
        self.created.append(name)


class _FakeClient:
    def __init__(self):
        self.containers = _FakeContainers()
        self.volumes = _FakeVolumes()


@pytest.fixture
def fake_client(monkeypatch):
    client = _FakeClient()
    monkeypatch.setattr(model_library_service, "_get_client", lambda: client)
    return client


def test_start_download_creates_volume_and_launches_container(fake_client):
    template = _model_template()

    updated = model_library_service.start_download(template)

    assert updated.spec.library_status is LibraryStatus.DOWNLOADING
    assert updated.spec.volume_name == "grastorp-model-mistralai-mixtral-8x7b-instruct-v0.1"
    assert updated.spec.library_progress_percent == 0.0
    assert fake_client.volumes.created == [updated.spec.volume_name]
    assert len(fake_client.containers.run_calls) == 1
    assert fake_client.containers.run_calls[0]["environment"]["REPO_ID"] == template.spec.repo_id


def test_start_download_idempotent_when_already_running(fake_client):
    template = _model_template()
    first = model_library_service.start_download(template)

    second = model_library_service.start_download(first)

    assert len(fake_client.containers.run_calls) == 1  # non rilanciato
    assert second.spec.library_status is LibraryStatus.DOWNLOADING


def test_get_status_updates_progress_while_running(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING, volume_name="vol-1")
    container = _FakeContainer(status="running", logs=json.dumps({"done": 3, "total": 10}).encode())
    fake_client.containers._by_name[model_library_service._downloader_container_name(template.id)] = container

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.DOWNLOADING
    assert updated.spec.library_progress_percent == 30.0


def test_get_status_marks_ready_on_successful_exit(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING, volume_name="vol-1")
    container = _FakeContainer(status="exited", exit_code=0)
    fake_client.containers._by_name[model_library_service._downloader_container_name(template.id)] = container

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.READY
    assert updated.spec.library_progress_percent == 100.0
    assert updated.spec.downloaded_at is not None
    assert container.removed is True


def test_get_status_marks_error_on_failed_exit(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING, volume_name="vol-1")
    logs = json.dumps({"error": "repo privato, accesso negato"}).encode()
    container = _FakeContainer(status="exited", exit_code=1, logs=logs)
    fake_client.containers._by_name[model_library_service._downloader_container_name(template.id)] = container

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.ERROR
    assert "accesso negato" in updated.spec.library_error


def test_get_status_marks_error_when_container_missing(fake_client):
    template = _model_template(library_status=LibraryStatus.DOWNLOADING, volume_name="vol-1")

    updated = model_library_service.get_status(template)

    assert updated.spec.library_status is LibraryStatus.ERROR
    assert "non trovato" in updated.spec.library_error


def test_get_status_noop_when_not_downloading(fake_client):
    template = _model_template(library_status=LibraryStatus.READY, volume_name="vol-1")

    updated = model_library_service.get_status(template)

    assert updated == template
    assert fake_client.containers.run_calls == []


def test_verify_library_marks_ready_when_files_match(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.READY, volume_name="vol-1")
    monkeypatch.setattr(
        hf_metadata_service,
        "list_safetensor_files",
        lambda repo_id: [{"path": "model-00001.safetensors", "size": 100}],
    )
    found = json.dumps([{"name": "model-00001.safetensors", "size": 100}]).encode()
    original_run = fake_client.containers.run
    fake_client.containers.run = lambda image, **kwargs: _FakeContainer(status="exited", exit_code=0, logs=found)

    updated = model_library_service.verify_library(template)

    assert updated.spec.library_status is LibraryStatus.READY
    assert updated.spec.library_error is None


def test_verify_library_marks_error_when_file_missing(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.READY, volume_name="vol-1")
    monkeypatch.setattr(
        hf_metadata_service,
        "list_safetensor_files",
        lambda repo_id: [{"path": "model-00001.safetensors", "size": 100}],
    )
    fake_client.containers.run = lambda image, **kwargs: _FakeContainer(status="exited", exit_code=0, logs=b"[]")

    updated = model_library_service.verify_library(template)

    assert updated.spec.library_status is LibraryStatus.ERROR
    assert "mancanti" in updated.spec.library_error


def test_verify_library_raises_without_reference_data(fake_client, monkeypatch):
    template = _model_template(library_status=LibraryStatus.READY, volume_name="vol-1")
    monkeypatch.setattr(hf_metadata_service, "list_safetensor_files", lambda repo_id: [])

    with pytest.raises(model_library_service.ModelLibraryError):
        model_library_service.verify_library(template)


def test_delete_library_removes_volume_and_resets_spec(fake_client):
    template = _model_template(
        library_status=LibraryStatus.READY, volume_name="vol-1", library_progress_percent=100.0
    )
    fake_client.volumes.create("vol-1")

    updated = model_library_service.delete_library(template)

    assert updated.spec.library_status is LibraryStatus.NOT_DOWNLOADED
    assert updated.spec.volume_name is None
    assert "vol-1" not in fake_client.volumes._names
