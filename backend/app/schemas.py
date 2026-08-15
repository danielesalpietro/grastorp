from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Framework(str, Enum):
    VLLM = "vllm"
    # stub per estensioni future
    TGI = "tgi"
    LLAMA_CPP = "llama_cpp"


class WebUI(str, Enum):
    NONE = "none"
    OPEN_WEBUI = "open_webui"
    TEXT_GENERATION_WEBUI = "text_generation_webui"


class DeploymentState(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ComputeMode(str, Enum):
    CPU = "cpu"
    GPU = "gpu"


class GPUDevice(BaseModel):
    """GPU NVIDIA rilevata sull'host (via nvidia-smi), esposta per la selezione in fase di deploy."""

    index: int
    name: str
    vram_total_mb: int
    vram_used_mb: int = 0
    vram_free_mb: int | None = None
    driver_version: str | None = None
    uuid: str | None = None
    pci_bus_id: str | None = None
    temperature_c: int | None = None
    utilization_percent: int | None = None
    power_draw_w: float | None = None
    power_limit_w: float | None = None
    compute_capability: str | None = None


class HostInfo(BaseModel):
    """Info sul docker daemon e sull'host reale che lo esegue."""

    hostname: str | None
    operating_system: str | None
    os_type: str | None
    kernel_version: str | None
    architecture: str | None
    cpu_count: int | None
    mem_total_bytes: int | None
    docker_version: str | None
    containers_total: int | None
    containers_running: int | None
    images_count: int | None


class NICDevice(BaseModel):
    """Interfaccia di rete disponibile sull'host, selezionabile come in ESXi."""

    name: str
    address: str | None = None


class DatastoreType(str, Enum):
    LOCAL = "local"
    # LUN condivisa via iSCSI: stub, non ancora supportato (vedi DatastoreCreateRequest).
    ISCSI = "iscsi"
    NFS = "nfs"


class Datastore(BaseModel):
    """Storage su cui possono risiedere risorse condivise come la Model Library.

    Rispecchia il concetto di datastore vSphere: locale (disco host), condiviso via
    iSCSI (stub futuro) o su mount point di rete (NFS, già supportato nativamente
    dal driver 'local' di Docker passando i driver_opts giusti).
    """

    id: str
    name: str
    type: DatastoreType
    nfs_server: str | None = None
    nfs_export_path: str | None = None
    nfs_options: str = "rw,nfsvers=4"
    created_at: str


class DatastoreCreateRequest(BaseModel):
    name: str
    type: DatastoreType
    nfs_server: str | None = None
    nfs_export_path: str | None = None
    nfs_options: str = "rw,nfsvers=4"

    @model_validator(mode="after")
    def _validate_type_fields(self) -> "DatastoreCreateRequest":
        if self.type is DatastoreType.ISCSI:
            raise ValueError("Datastore iSCSI non ancora supportato")
        if self.type is DatastoreType.NFS and not (self.nfs_server and self.nfs_export_path):
            raise ValueError("Datastore NFS richiede nfs_server e nfs_export_path")
        return self


class LibraryConfig(BaseModel):
    """Impostazione globale: su quale datastore risiede la Model Library condivisa."""

    datastore_id: str = "local"


class RegistryProvider(str, Enum):
    HUGGINGFACE = "huggingface"
    # Endpoint compatibile con le REST API di Hugging Face Hub (es. mirror
    # aziendale/self-hosted), non un provider diverso: stessa integrazione,
    # solo base_url/api_key diversi.
    CUSTOM = "custom"


class ModelRegistry(BaseModel):
    """Sorgente da cui cercare modelli e ricavarne le caratteristiche tecniche.

    Il registry Hugging Face di default (id 'huggingface') è seminato
    all'avvio e non può essere disabilitato né eliminato.
    """

    id: str
    name: str
    provider: RegistryProvider
    base_url: str
    api_key: str | None = None
    enabled: bool = True
    created_at: str


class ModelRegistryCreateRequest(BaseModel):
    name: str
    provider: RegistryProvider = RegistryProvider.CUSTOM
    base_url: str | None = None
    api_key: str | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def _validate_base_url(self) -> "ModelRegistryCreateRequest":
        if self.provider is RegistryProvider.CUSTOM and not self.base_url:
            raise ValueError("Un registry custom richiede base_url")
        return self


class OffloadConfig(BaseModel):
    enabled: bool = False
    cpu_offload_gb: float = Field(default=0, ge=0)


class ResourceConfig(BaseModel):
    cpu_cores: int = Field(default=4, ge=1)
    ram_gb: int = Field(default=16, ge=1)
    compute_mode: ComputeMode = ComputeMode.GPU
    gpu_indices: list[int] = Field(default_factory=list)
    vram_limit_gb: float | None = None
    offload: OffloadConfig = Field(default_factory=OffloadConfig)


class NetworkConfig(BaseModel):
    bind_ip: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    nics: list[str] = Field(default_factory=list)


class DeploymentCreateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    model_repo_id: str
    framework: Framework = Framework.VLLM
    webui: WebUI = WebUI.NONE
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)


class Deployment(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    name: str
    model_repo_id: str
    framework: Framework
    webui: WebUI
    resources: ResourceConfig
    network: NetworkConfig
    state: DeploymentState
    container_id: str | None = None
    library_volume: str | None = None
    created_at: str


class TemplateType(str, Enum):
    MODEL = "model"
    DOCKER_REGISTRY = "docker_registry"


class LibraryStatus(str, Enum):
    """Stato del download dei pesi del modello nella Library condivisa (volume Docker)."""

    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    READY = "ready"
    ERROR = "error"


class ModelTemplateSpec(BaseModel):
    """Caratteristiche tecniche di un modello (MoE o dense)."""

    model_config = ConfigDict(protected_namespaces=())

    repo_id: str
    registry_id: str = "huggingface"
    architecture: str
    num_experts: int | None = None
    num_experts_active: int | None = None
    num_layers: int | None = None
    params_billion: float | None = None
    shard_size_gb: float | None = None
    num_shards: int | None = None
    context_length: int | None = None
    quantization: str | None = None

    # Library: tracciano se i pesi sono già stati scaricati nel volume Library
    # condiviso, per evitare di scaricarli una volta per ogni deployment.
    library_status: LibraryStatus = LibraryStatus.NOT_DOWNLOADED
    library_progress_percent: float | None = None
    library_error: str | None = None
    downloaded_at: str | None = None


class DockerRegistryTemplateSpec(BaseModel):
    """Caratteristiche tecniche di un container pronto per il deploy, scaricabile da un registry."""

    registry: str
    image: str
    tag: str = "latest"
    size_gb: float | None = None
    ram_required_mb: int | None = None
    gpu_required: bool = False
    gpu_compatible: list[str] = Field(default_factory=list)
    min_vram_mb: int | None = None
    cuda_version: str | None = None


class TemplateCreateRequest(BaseModel):
    type: TemplateType
    name: str
    description: str = ""
    enabled: bool = True
    spec: ModelTemplateSpec | DockerRegistryTemplateSpec

    @model_validator(mode="after")
    def _spec_matches_type(self) -> "TemplateCreateRequest":
        expected = ModelTemplateSpec if self.type is TemplateType.MODEL else DockerRegistryTemplateSpec
        if not isinstance(self.spec, expected):
            raise ValueError(f"spec non compatibile con type={self.type.value}")
        return self


class Template(BaseModel):
    id: str
    type: TemplateType
    name: str
    description: str = ""
    enabled: bool = True
    spec: ModelTemplateSpec | DockerRegistryTemplateSpec
    created_at: str

    @model_validator(mode="after")
    def _spec_matches_type(self) -> "Template":
        expected = ModelTemplateSpec if self.type is TemplateType.MODEL else DockerRegistryTemplateSpec
        if not isinstance(self.spec, expected):
            raise ValueError(f"spec non compatibile con type={self.type.value}")
        return self


class TemplateFromRegistryRequest(BaseModel):
    """Crea un template modello interrogando un registry per le caratteristiche tecniche."""

    model_config = ConfigDict(protected_namespaces=())

    registry_id: str
    repo_id: str
    name: str | None = None
    description: str = ""
    enabled: bool = True
