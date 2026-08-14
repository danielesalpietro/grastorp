from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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


class HFModel(BaseModel):
    """Voce del catalogo modelli Hugging Face disponibili per il deploy."""

    repo_id: str
    display_name: str
    architecture: ModelArchitecture
    num_experts: int | None = None
    params_billion: float | None = None
    description: str = ""


class GPUDevice(BaseModel):
    """GPU rilevata sull'host, esposta per la selezione in fase di deploy."""

    index: int
    name: str
    vram_total_mb: int
    vram_used_mb: int = 0


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
