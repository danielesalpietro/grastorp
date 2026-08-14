import { useEffect, useState } from "react";
import { api, GPUDevice, HostInfo } from "../../api/client";

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
}

export function HostManage() {
  const [hostInfo, setHostInfo] = useState<HostInfo | null>(null);
  const [hostInfoError, setHostInfoError] = useState<string | null>(null);
  const [gpus, setGpus] = useState<GPUDevice[]>([]);

  useEffect(() => {
    api
      .getHostInfo()
      .then(setHostInfo)
      .catch((e) => setHostInfoError((e as Error).message));
    api.listGpus().then(setGpus);
  }, []);

  return (
    <div>
      <h1 className="page-title">Host</h1>
      <p className="page-subtitle">Gestione dell'host su cui girano i deployment.</p>

      <div className="panel">
        <p style={{ fontWeight: 600 }}>System</p>
        {hostInfoError ? (
          <span className="stub-note">{hostInfoError}</span>
        ) : !hostInfo ? (
          <p>Caricamento...</p>
        ) : (
          <>
            <p>Hostname: {hostInfo.hostname ?? "—"}</p>
            <p>
              Sistema operativo: {hostInfo.operating_system ?? "—"} ({hostInfo.os_type ?? "—"},{" "}
              {hostInfo.architecture ?? "—"})
            </p>
            <p>Kernel: {hostInfo.kernel_version ?? "—"}</p>
            <p>CPU: {hostInfo.cpu_count ?? "—"} core</p>
            <p>RAM totale: {formatBytes(hostInfo.mem_total_bytes)}</p>
            <p>Docker: {hostInfo.docker_version ?? "—"}</p>
            <p>
              Container: {hostInfo.containers_running ?? "—"} in esecuzione / {hostInfo.containers_total ?? "—"}{" "}
              totali · Immagini: {hostInfo.images_count ?? "—"}
            </p>
          </>
        )}

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
