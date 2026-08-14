import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, Deployment } from "../api/client";
import { useTasks } from "../context/TasksContext";

function StateBadge({ state }: { state: Deployment["state"] }) {
  return <span className={`badge badge--${state}`}>{state}</span>;
}

export function Deployments() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { pushTask } = useTasks();
  const navigate = useNavigate();

  const reload = useCallback(() => {
    setLoading(true);
    api
      .listDeployments()
      .then(setDeployments)
      .finally(() => setLoading(false));
  }, []);

  useEffect(reload, [reload]);

  async function handleStart(id: string) {
    pushTask(`Avvio deployment ${id}`, "running");
    try {
      await api.startDeployment(id);
      pushTask(`Deployment ${id} avviato`, "success");
    } catch (e) {
      pushTask(`Avvio fallito: ${(e as Error).message}`, "error");
    }
    reload();
  }

  async function handleStop(id: string) {
    pushTask(`Arresto deployment ${id}`, "running");
    try {
      await api.stopDeployment(id);
      pushTask(`Deployment ${id} arrestato`, "success");
    } catch (e) {
      pushTask(`Arresto fallito: ${(e as Error).message}`, "error");
    }
    reload();
  }

  async function handleDelete(id: string) {
    if (!confirm("Eliminare questo deployment?")) return;
    try {
      await api.deleteDeployment(id);
      pushTask(`Deployment ${id} eliminato`, "success");
    } catch (e) {
      pushTask(`Eliminazione fallita: ${(e as Error).message}`, "error");
    }
    setSelected(null);
    reload();
  }

  return (
    <div>
      <h1 className="page-title">Deployments</h1>
      <p className="page-subtitle">Container di modelli MoE in esecuzione o configurati su questo host.</p>

      <div className="toolbar">
        <button className="btn btn--primary" onClick={() => navigate("/deployments/new")}>
          + New Deployment
        </button>
        <button className="btn" disabled={!selected} onClick={() => selected && handleStart(selected)}>
          Start
        </button>
        <button className="btn" disabled={!selected} onClick={() => selected && handleStop(selected)}>
          Stop
        </button>
        <button className="btn btn--danger" disabled={!selected} onClick={() => selected && handleDelete(selected)}>
          Delete
        </button>
      </div>

      {loading ? (
        <p>Caricamento...</p>
      ) : deployments.length === 0 ? (
        <div className="empty-state">Nessun deployment. Crea il primo con "New Deployment".</div>
      ) : (
        <table className="grid">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Modello</th>
              <th>Framework</th>
              <th>Stato</th>
              <th>CPU</th>
              <th>RAM</th>
              <th>GPU</th>
              <th>Endpoint</th>
            </tr>
          </thead>
          <tbody>
            {deployments.map((d) => (
              <tr
                key={d.id}
                className={selected === d.id ? "selected" : ""}
                onClick={() => setSelected(d.id)}
              >
                <td>
                  <Link to={`/deployments/${d.id}`}>{d.name}</Link>
                </td>
                <td>{d.model_repo_id}</td>
                <td>{d.framework}</td>
                <td>
                  <StateBadge state={d.state} />
                </td>
                <td>{d.resources.cpu_cores}</td>
                <td>{d.resources.ram_gb} GB</td>
                <td>{d.resources.gpu_indices.length ? d.resources.gpu_indices.join(", ") : "—"}</td>
                <td>
                  {d.network.bind_ip}:{d.network.api_port}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
