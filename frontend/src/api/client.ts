export interface GPUDevice {
  index: number;
  name: string;
  vram_total_mb: number;
  vram_used_mb: number;
  vram_free_mb: number | null;
  driver_version: string | null;
  uuid: string | null;
  pci_bus_id: string | null;
  temperature_c: number | null;
  utilization_percent: number | null;
  power_draw_w: number | null;
  power_limit_w: number | null;
  compute_capability: string | null;
}

export interface NICDevice {
  name: string;
  address: string | null;
}

export interface HostInfo {
  hostname: string | null;
  operating_system: string | null;
  os_type: string | null;
  kernel_version: string | null;
  architecture: string | null;
  cpu_count: number | null;
  mem_total_bytes: number | null;
  docker_version: string | null;
  containers_total: number | null;
  containers_running: number | null;
  images_count: number | null;
}

export interface OffloadConfig {
  enabled: boolean;
  cpu_offload_gb: number;
}

export type ComputeMode = "cpu" | "gpu";

export interface ResourceConfig {
  cpu_cores: number;
  ram_gb: number;
  compute_mode: ComputeMode;
  gpu_indices: number[];
  vram_limit_gb: number | null;
  offload: OffloadConfig;
}

export interface NetworkConfig {
  bind_ip: string;
  api_port: number;
  nics: string[];
}

export type Framework = "vllm" | "tgi" | "llama_cpp";
export type WebUI = "none" | "open_webui" | "text_generation_webui";
export type DeploymentState = "creating" | "running" | "stopped" | "error";

export interface Deployment {
  id: string;
  name: string;
  model_repo_id: string;
  framework: Framework;
  webui: WebUI;
  resources: ResourceConfig;
  network: NetworkConfig;
  state: DeploymentState;
  container_id: string | null;
  library_volume: string | null;
  created_at: string;
}

export interface DeploymentCreateRequest {
  name: string;
  model_repo_id: string;
  framework: Framework;
  webui: WebUI;
  resources: ResourceConfig;
  network: NetworkConfig;
}

export interface OptionEntry {
  id: string;
  label: string;
  available: boolean;
}

export type TemplateType = "model" | "docker_registry";

export type LibraryStatus = "not_downloaded" | "downloading" | "ready" | "error";

export interface ModelTemplateSpec {
  repo_id: string;
  architecture: string;
  num_experts: number | null;
  num_experts_active: number | null;
  num_layers: number | null;
  params_billion: number | null;
  shard_size_gb: number | null;
  num_shards: number | null;
  context_length: number | null;
  quantization: string | null;
  volume_name: string | null;
  library_status: LibraryStatus;
  library_progress_percent: number | null;
  library_error: string | null;
  downloaded_at: string | null;
}

export interface DockerRegistryTemplateSpec {
  registry: string;
  image: string;
  tag: string;
  size_gb: number | null;
  ram_required_mb: number | null;
  gpu_required: boolean;
  gpu_compatible: string[];
  min_vram_mb: number | null;
  cuda_version: string | null;
}

export interface Template {
  id: string;
  type: TemplateType;
  name: string;
  description: string;
  enabled: boolean;
  spec: ModelTemplateSpec | DockerRegistryTemplateSpec;
  created_at: string;
}

export interface TemplateCreateRequest {
  type: TemplateType;
  name: string;
  description: string;
  enabled: boolean;
  spec: ModelTemplateSpec | DockerRegistryTemplateSpec;
}

export interface TemplateFromHFRequest {
  repo_id: string;
  name?: string;
  description?: string;
  enabled?: boolean;
}

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Richiesta fallita: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  health: () => request<{ status: string; docker: boolean }>("/health"),
  getHostInfo: () => request<HostInfo>("/system/host"),
  listGpus: () => request<GPUDevice[]>("/system/gpus"),
  listNics: () => request<NICDevice[]>("/system/nics"),
  listFrameworks: () => request<OptionEntry[]>("/system/frameworks"),
  listWebuis: () => request<OptionEntry[]>("/system/webuis"),
  listDeployments: () => request<Deployment[]>("/deployments"),
  getDeployment: (id: string) => request<Deployment>(`/deployments/${id}`),
  createDeployment: (payload: DeploymentCreateRequest) =>
    request<Deployment>("/deployments", { method: "POST", body: JSON.stringify(payload) }),
  deleteDeployment: (id: string) => request<void>(`/deployments/${id}`, { method: "DELETE" }),
  startDeployment: (id: string) => request<Deployment>(`/deployments/${id}/start`, { method: "POST" }),
  stopDeployment: (id: string) => request<Deployment>(`/deployments/${id}/stop`, { method: "POST" }),
  listTemplates: (type?: TemplateType, enabled?: boolean) => {
    const params = new URLSearchParams();
    if (type) params.set("type", type);
    if (enabled !== undefined) params.set("enabled", String(enabled));
    const qs = params.toString();
    return request<Template[]>(`/templates${qs ? `?${qs}` : ""}`);
  },
  getTemplate: (id: string) => request<Template>(`/templates/${id}`),
  createTemplate: (payload: TemplateCreateRequest) =>
    request<Template>("/templates", { method: "POST", body: JSON.stringify(payload) }),
  createTemplateFromHF: (payload: TemplateFromHFRequest) =>
    request<Template>("/templates/from-hf", { method: "POST", body: JSON.stringify(payload) }),
  syncTemplateFromHF: (id: string) => request<Template>(`/templates/${id}/sync-hf`, { method: "POST" }),
  downloadToLibrary: (id: string) => request<Template>(`/templates/${id}/library/download`, { method: "POST" }),
  getLibraryStatus: (id: string) => request<Template>(`/templates/${id}/library`),
  verifyLibrary: (id: string) => request<Template>(`/templates/${id}/library/verify`, { method: "POST" }),
  deleteLibrary: (id: string) => request<Template>(`/templates/${id}/library`, { method: "DELETE" }),
  updateTemplate: (id: string, payload: TemplateCreateRequest) =>
    request<Template>(`/templates/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTemplate: (id: string) => request<void>(`/templates/${id}`, { method: "DELETE" }),
};
