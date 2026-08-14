export type ModelArchitecture = "moe";

export interface HFModel {
  repo_id: string;
  display_name: string;
  architecture: ModelArchitecture;
  num_experts: number | null;
  params_billion: number | null;
  description: string;
}

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

export interface ResourceConfig {
  cpu_cores: number;
  ram_gb: number;
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
  listModels: () => request<HFModel[]>("/models"),
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
};
