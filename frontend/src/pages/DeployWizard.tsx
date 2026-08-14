import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  ComputeMode,
  DeploymentCreateRequest,
  Framework,
  GPUDevice,
  HFModel,
  NICDevice,
  OptionEntry,
  WebUI,
} from "../api/client";
import { useTasks } from "../context/TasksContext";

const STEPS = ["Modello", "Framework", "Risorse", "Rete", "WebUI", "Verifica"] as const;

function defaultForm(): DeploymentCreateRequest {
  return {
    name: "",
    model_repo_id: "",
    framework: "vllm",
    webui: "none",
    resources: {
      cpu_cores: 4,
      ram_gb: 16,
      compute_mode: "gpu",
      gpu_indices: [],
      vram_limit_gb: null,
      offload: { enabled: false, cpu_offload_gb: 0 },
    },
    network: { bind_ip: "0.0.0.0", api_port: 8000, nics: [] },
  };
}

export function DeployWizard() {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<DeploymentCreateRequest>(defaultForm());
  const [models, setModels] = useState<HFModel[]>([]);
  const [gpus, setGpus] = useState<GPUDevice[]>([]);
  const [nics, setNics] = useState<NICDevice[]>([]);
  const [frameworks, setFrameworks] = useState<OptionEntry[]>([]);
  const [webuis, setWebuis] = useState<OptionEntry[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { pushTask } = useTasks();
  const navigate = useNavigate();

  useEffect(() => {
    api.listModels().then(setModels);
    api.listGpus().then(setGpus);
    api.listNics().then(setNics);
    api.listFrameworks().then(setFrameworks);
    api.listWebuis().then(setWebuis);
  }, []);

  function update<K extends keyof DeploymentCreateRequest>(key: K, value: DeploymentCreateRequest[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function setComputeMode(mode: ComputeMode) {
    setForm((f) => ({
      ...f,
      resources:
        mode === "cpu"
          ? { ...f.resources, compute_mode: mode, gpu_indices: [], offload: { enabled: false, cpu_offload_gb: 0 } }
          : { ...f.resources, compute_mode: mode },
    }));
  }

  function toggleGpu(index: number) {
    setForm((f) => {
      const has = f.resources.gpu_indices.includes(index);
      const gpu_indices = has
        ? f.resources.gpu_indices.filter((i) => i !== index)
        : [...f.resources.gpu_indices, index];
      return { ...f, resources: { ...f.resources, gpu_indices } };
    });
  }

  function toggleNic(name: string) {
    setForm((f) => {
      const has = f.network.nics.includes(name);
      const nics = has ? f.network.nics.filter((n) => n !== name) : [...f.network.nics, name];
      return { ...f, network: { ...f.network, nics } };
    });
  }

  const canGoNext = (): boolean => {
    switch (step) {
      case 0:
        return form.model_repo_id !== "";
      case 1:
        return form.framework !== undefined;
      default:
        return true;
    }
  };

  async function submit() {
    setSubmitting(true);
    setError(null);
    pushTask(`Creazione deployment "${form.name}"`, "running");
    try {
      const deployment = await api.createDeployment(form);
      pushTask(`Deployment "${form.name}" creato`, "success");
      navigate(`/deployments/${deployment.id}`);
    } catch (e) {
      const message = (e as Error).message;
      setError(message);
      pushTask(`Creazione fallita: ${message}`, "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">New Deployment</h1>
      <p className="page-subtitle">Distribuisci un modello Mixture-of-Experts come container.</p>

      <div className="wizard">
        <div className="wizard__steps">
          {STEPS.map((label, i) => (
            <div
              key={label}
              className={"wizard__step" + (i === step ? " active" : i < step ? " done" : "")}
              onClick={() => i < step && setStep(i)}
              style={{ cursor: i < step ? "pointer" : "default" }}
            >
              {i + 1}. {label}
            </div>
          ))}
        </div>

        <div className="wizard__content">
          {step === 0 && (
            <div className="panel">
              <p>Seleziona un modello MoE da Hugging Face.</p>
              {models.map((m) => (
                <div
                  key={m.repo_id}
                  className={"model-card" + (form.model_repo_id === m.repo_id ? " selected" : "")}
                  onClick={() => update("model_repo_id", m.repo_id)}
                >
                  <div className="model-card__title">{m.display_name}</div>
                  <div className="model-card__meta">
                    {m.repo_id} · {m.num_experts} esperti · {m.params_billion}B parametri
                  </div>
                  <div className="model-card__meta">{m.description}</div>
                </div>
              ))}
            </div>
          )}

          {step === 1 && (
            <div className="panel">
              <p>Framework di inferenza.</p>
              {frameworks.map((f) => (
                <div key={f.id} className="form-field checkbox">
                  <input
                    type="radio"
                    id={`fw-${f.id}`}
                    name="framework"
                    disabled={!f.available}
                    checked={form.framework === f.id}
                    onChange={() => update("framework", f.id as Framework)}
                  />
                  <label htmlFor={`fw-${f.id}`}>
                    {f.label} {!f.available && <span className="stub-note">non ancora disponibile</span>}
                  </label>
                </div>
              ))}
            </div>
          )}

          {step === 2 && (
            <div className="panel">
              <div className="form-field" style={{ marginBottom: 16 }}>
                <label>Modalità di calcolo</label>
                <div className="form-field checkbox">
                  <input
                    type="radio"
                    id="mode-gpu"
                    name="compute-mode"
                    checked={form.resources.compute_mode === "gpu"}
                    onChange={() => setComputeMode("gpu")}
                  />
                  <label htmlFor="mode-gpu">GPU</label>
                </div>
                <div className="form-field checkbox">
                  <input
                    type="radio"
                    id="mode-cpu"
                    name="compute-mode"
                    checked={form.resources.compute_mode === "cpu"}
                    onChange={() => setComputeMode("cpu")}
                  />
                  <label htmlFor="mode-cpu">CPU Only</label>
                </div>
              </div>

              <div className="form-row">
                <div className="form-field">
                  <label>CPU (core)</label>
                  <input
                    type="number"
                    min={1}
                    value={form.resources.cpu_cores}
                    onChange={(e) =>
                      update("resources", { ...form.resources, cpu_cores: Number(e.target.value) })
                    }
                  />
                </div>
                <div className="form-field">
                  <label>RAM (GB)</label>
                  <input
                    type="number"
                    min={1}
                    value={form.resources.ram_gb}
                    onChange={(e) => update("resources", { ...form.resources, ram_gb: Number(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>Limite vRAM (GB, opzionale)</label>
                  <input
                    type="number"
                    min={0}
                    value={form.resources.vram_limit_gb ?? ""}
                    onChange={(e) =>
                      update("resources", {
                        ...form.resources,
                        vram_limit_gb: e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </div>
              </div>

              <div className="form-field">
                <label>
                  GPU disponibili{" "}
                  {form.resources.compute_mode === "cpu" && (
                    <span className="stub-note">disponibile solo in modalità GPU</span>
                  )}
                </label>
                {gpus.length === 0 ? (
                  <span className="stub-note">Nessuna GPU rilevata sull'host (o rilevamento non disponibile)</span>
                ) : (
                  gpus.map((g) => (
                    <div key={g.index} className="form-field checkbox">
                      <input
                        type="checkbox"
                        id={`gpu-${g.index}`}
                        disabled={form.resources.compute_mode === "cpu"}
                        checked={form.resources.gpu_indices.includes(g.index)}
                        onChange={() => toggleGpu(g.index)}
                      />
                      <label htmlFor={`gpu-${g.index}`}>
                        GPU {g.index}: {g.name} ({g.vram_total_mb} MB)
                      </label>
                    </div>
                  ))
                )}
              </div>

              <div className="form-field checkbox">
                <input
                  type="checkbox"
                  id="offload-enabled"
                  disabled={form.resources.compute_mode === "cpu"}
                  checked={form.resources.offload.enabled}
                  onChange={(e) =>
                    update("resources", {
                      ...form.resources,
                      offload: { ...form.resources.offload, enabled: e.target.checked },
                    })
                  }
                />
                <label htmlFor="offload-enabled">
                  Abilita CPU offload{" "}
                  {form.resources.compute_mode === "cpu" && (
                    <span className="stub-note">disponibile solo in modalità GPU</span>
                  )}
                </label>
              </div>
              {form.resources.compute_mode === "gpu" && form.resources.offload.enabled && (
                <div className="form-field" style={{ maxWidth: 240 }}>
                  <label>Quantità di offload (GB)</label>
                  <input
                    type="number"
                    min={0}
                    value={form.resources.offload.cpu_offload_gb}
                    onChange={(e) =>
                      update("resources", {
                        ...form.resources,
                        offload: { ...form.resources.offload, cpu_offload_gb: Number(e.target.value) },
                      })
                    }
                  />
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="panel">
              <div className="form-row">
                <div className="form-field">
                  <label>IP di binding</label>
                  <input
                    type="text"
                    value={form.network.bind_ip}
                    onChange={(e) => update("network", { ...form.network, bind_ip: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Porta API</label>
                  <input
                    type="number"
                    value={form.network.api_port}
                    onChange={(e) =>
                      update("network", { ...form.network, api_port: Number(e.target.value) })
                    }
                  />
                </div>
              </div>
              <div className="form-field">
                <label>Schede di rete aggiuntive</label>
                {nics.length === 0 ? (
                  <span className="stub-note">Rilevamento NIC host non ancora implementato</span>
                ) : (
                  nics.map((n) => (
                    <div key={n.name} className="form-field checkbox">
                      <input
                        type="checkbox"
                        id={`nic-${n.name}`}
                        checked={form.network.nics.includes(n.name)}
                        onChange={() => toggleNic(n.name)}
                      />
                      <label htmlFor={`nic-${n.name}`}>
                        {n.name} {n.address ? `(${n.address})` : ""}
                      </label>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="panel">
              <p>WebUI da esporre insieme all'endpoint API.</p>
              {webuis.map((w) => (
                <div key={w.id} className="form-field checkbox">
                  <input
                    type="radio"
                    id={`webui-${w.id}`}
                    name="webui"
                    disabled={!w.available}
                    checked={form.webui === w.id}
                    onChange={() => update("webui", w.id as WebUI)}
                  />
                  <label htmlFor={`webui-${w.id}`}>
                    {w.label} {!w.available && <span className="stub-note">non ancora disponibile</span>}
                  </label>
                </div>
              ))}
            </div>
          )}

          {step === 5 && (
            <div className="panel">
              <div className="form-field" style={{ maxWidth: 320, marginBottom: 16 }}>
                <label>Nome deployment</label>
                <input type="text" value={form.name} onChange={(e) => update("name", e.target.value)} />
              </div>
              <p>
                <strong>Modello:</strong> {form.model_repo_id || "—"}
              </p>
              <p>
                <strong>Framework:</strong> {form.framework}
              </p>
              <p>
                <strong>CPU / RAM:</strong> {form.resources.cpu_cores} core / {form.resources.ram_gb} GB
              </p>
              <p>
                <strong>Modalità:</strong> {form.resources.compute_mode === "gpu" ? "GPU" : "CPU Only"}
              </p>
              {form.resources.compute_mode === "gpu" && (
                <>
                  <p>
                    <strong>GPU:</strong>{" "}
                    {form.resources.gpu_indices.length ? form.resources.gpu_indices.join(", ") : "nessuna"}
                  </p>
                  <p>
                    <strong>Offload:</strong>{" "}
                    {form.resources.offload.enabled
                      ? `${form.resources.offload.cpu_offload_gb} GB`
                      : "disabilitato"}
                  </p>
                </>
              )}
              <p>
                <strong>Endpoint:</strong> {form.network.bind_ip}:{form.network.api_port}
              </p>
              <p>
                <strong>WebUI:</strong> {form.webui}
              </p>
              {error && <p style={{ color: "var(--error)" }}>{error}</p>}
            </div>
          )}

          <div className="toolbar">
            <button className="btn" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
              Indietro
            </button>
            {step < STEPS.length - 1 ? (
              <button className="btn btn--primary" disabled={!canGoNext()} onClick={() => setStep((s) => s + 1)}>
                Avanti
              </button>
            ) : (
              <button
                className="btn btn--primary"
                disabled={submitting || !form.name || !form.model_repo_id}
                onClick={submit}
              >
                {submitting ? "Creazione..." : "Crea Deployment"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
