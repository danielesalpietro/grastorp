import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, Deployment } from "../api/client";
import { useTasks } from "../context/TasksContext";

const TABS = ["Summary", "Configuration", "Monitor", "Console"] as const;

export function ModelConfiguration() {
  const { id } = useParams<{ id: string }>();
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Summary");
  const { pushTask } = useTasks();
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) return;
    api.getDeployment(id).then(setDeployment);
  }, [id]);

  if (!deployment) return <p>Caricamento...</p>;

  async function reload() {
    if (!id) return;
    setDeployment(await api.getDeployment(id));
  }

  async function handleStart() {
    if (!id) return;
    pushTask(`Avvio ${deployment?.name}`, "running");
    try {
      await api.startDeployment(id);
      pushTask(`${deployment?.name} avviato`, "success");
    } catch (e) {
      pushTask(`Avvio fallito: ${(e as Error).message}`, "error");
    }
    reload();
  }

  async function handleStop() {
    if (!id) return;
    pushTask(`Arresto ${deployment?.name}`, "running");
    try {
      await api.stopDeployment(id);
      pushTask(`${deployment?.name} arrestato`, "success");
    } catch (e) {
      pushTask(`Arresto fallito: ${(e as Error).message}`, "error");
    }
    reload();
  }

  return (
    <div>
      <button className="btn" onClick={() => navigate("/deployments")} style={{ marginBottom: 12 }}>
        ← Deployments
      </button>
      <h1 className="page-title">
        {deployment.name} <span className={`badge badge--${deployment.state}`}>{deployment.state}</span>
      </h1>
      <p className="page-subtitle">{deployment.model_repo_id}</p>

      <div className="toolbar">
        <button className="btn btn--primary" disabled={deployment.state === "running"} onClick={handleStart}>
          Start
        </button>
        <button className="btn" disabled={deployment.state !== "running"} onClick={handleStop}>
          Stop
        </button>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <div key={t} className={"tab" + (tab === t ? " active" : "")} onClick={() => setTab(t)}>
            {t}
          </div>
        ))}
      </div>

      {tab === "Summary" && (
        <div className="panel">
          <p>
            <strong>Framework:</strong> {deployment.framework}
          </p>
          <p>
            <strong>WebUI:</strong> {deployment.webui}
          </p>
          <p>
            <strong>Container ID:</strong> {deployment.container_id ?? "—"}
          </p>
          <p>
            <strong>Creato il:</strong> {new Date(deployment.created_at).toLocaleString()}
          </p>
          <p>
            <strong>Endpoint API:</strong> http://{deployment.network.bind_ip}:{deployment.network.api_port}
          </p>
        </div>
      )}

      {tab === "Configuration" && (
        <div className="panel">
          <p style={{ fontWeight: 600 }}>Modello</p>
          <p>Repo Hugging Face: {deployment.model_repo_id}</p>

          <p style={{ fontWeight: 600, marginTop: 16 }}>Risorse</p>
          <p>CPU: {deployment.resources.cpu_cores} core</p>
          <p>RAM: {deployment.resources.ram_gb} GB</p>
          <p>Modalità: {deployment.resources.compute_mode === "gpu" ? "GPU" : "CPU Only"}</p>
          {deployment.resources.compute_mode === "gpu" && (
            <>
              <p>GPU: {deployment.resources.gpu_indices.join(", ") || "nessuna"}</p>
              <p>Limite vRAM: {deployment.resources.vram_limit_gb ?? "nessun limite"}</p>
              <p>
                CPU offload:{" "}
                {deployment.resources.offload.enabled
                  ? `abilitato (${deployment.resources.offload.cpu_offload_gb} GB)`
                  : "disabilitato"}
              </p>
            </>
          )}

          <p style={{ fontWeight: 600, marginTop: 16 }}>Rete</p>
          <p>
            Bind: {deployment.network.bind_ip}:{deployment.network.api_port}
          </p>
          <p>NIC aggiuntive: {deployment.network.nics.join(", ") || "nessuna"}</p>

          <span className="stub-note">La modifica della configurazione a runtime non è ancora implementata</span>
        </div>
      )}

      {tab === "Monitor" && (
        <div className="panel">
          <span className="stub-note">
            Metriche (throughput, latenza, utilizzo GPU/CPU) non ancora implementate
          </span>
        </div>
      )}

      {tab === "Console" && (
        <div className="panel">
          <span className="stub-note">Console/log streaming del container non ancora implementata</span>
        </div>
      )}
    </div>
  );
}
