from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelArchitecture(str, Enum):
    MIXTURE_OF_EXPERTS = "moe"


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


class HFModel(BaseModel):
    """Voce del catalogo modelli Hugging Face disponibili per il deploy."""

    repo_id: str
    display_name: str
    architecture: ModelArchitecture
    num_experts: int | None = None
    params_billion: float | None = None
    description: str = ""


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
    created_at: str


class TemplateType(str, Enum):
    MODEL = "model"
    DOCKER_REGISTRY = "docker_registry"


class ModelTemplateSpec(BaseModel):
    """Caratteristiche tecniche di un modello (MoE o dense)."""

    architecture: str
    num_experts: int | None = None
    num_experts_active: int | None = None
    num_layers: int | None = None
    params_billion: float | None = None
    shard_size_gb: float | None = None
    num_shards: int | None = None
    context_length: int | None = None
    quantization: str | None = None


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
    spec: ModelTemplateSpec | DockerRegistryTemplateSpec
    created_at: str

    @model_validator(mode="after")
    def _spec_matches_type(self) -> "Template":
        expected = ModelTemplateSpec if self.type is TemplateType.MODEL else DockerRegistryTemplateSpec
        if not isinstance(self.spec, expected):
            raise ValueError(f"spec non compatibile con type={self.type.value}")
        return self
