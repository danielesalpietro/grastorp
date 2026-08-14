import { useEffect, useState } from "react";
import { api, GPUDevice } from "../../api/client";

export function HostManage() {
  const [dockerOk, setDockerOk] = useState<boolean | null>(null);
  const [gpus, setGpus] = useState<GPUDevice[]>([]);

  useEffect(() => {
    api
      .health()
      .then((h) => setDockerOk(h.docker))
      .catch(() => setDockerOk(false));
    api.listGpus().then(setGpus);
  }, []);

  return (
    <div>
      <h1 className="page-title">Host</h1>
      <p className="page-subtitle">Gestione dell'host su cui girano i deployment.</p>

      <div className="panel">
        <p style={{ fontWeight: 600 }}>System</p>
        <p>Docker daemon: {dockerOk === null ? "..." : dockerOk ? "connesso" : "non disponibile"}</p>

        <p style={{ fontWeight: 600, marginTop: 16 }}>Hardware — GPU</p>
        {gpus.length === 0 ? (
          <span className="stub-note">Nessuna GPU rilevata sull'host (o rilevamento non disponibile)</span>
        ) : (
          <table className="grid" style={{ marginTop: 8 }}>
            <thead>
              <tr>
                <th>Indice</th>
                <th>Nome</th>
                <th>vRAM totale</th>
                <th>vRAM in uso</th>
              </tr>
            </thead>
            <tbody>
              {gpus.map((g) => (
                <tr key={g.index}>
                  <td>{g.index}</td>
                  <td>{g.name}</td>
                  <td>{g.vram_total_mb} MB</td>
                  <td>{g.vram_used_mb} MB</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <p style={{ fontWeight: 600, marginTop: 16 }}>
          Services <span className="stub-note">non ancora implementato</span>
        </p>
        <p style={{ fontWeight: 600, marginTop: 16 }}>
          Security &amp; users <span className="stub-note">non ancora implementato</span>
        </p>
      </div>
    </div>
  );
}
