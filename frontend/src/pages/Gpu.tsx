import { useEffect, useState } from "react";
import { api, GPUDevice } from "../api/client";

function fmt(value: number | string | null, suffix = ""): string {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

export function Gpu() {
  const [gpus, setGpus] = useState<GPUDevice[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listGpus()
      .then(setGpus)
      .catch((e) => setError((e as Error).message));
  }, []);

  return (
    <div>
      <h1 className="page-title">GPU</h1>
      <p className="page-subtitle">Schede NVIDIA rilevate sull'host, disponibili per l'assegnazione ai deployment.</p>

      {error ? (
        <div className="empty-state">{error}</div>
      ) : gpus === null ? (
        <p>Caricamento...</p>
      ) : gpus.length === 0 ? (
        <div className="empty-state">
          Nessuna GPU NVIDIA rilevata.
          <br />
          <span className="stub-note">
            Richiede nvidia-smi raggiungibile dal container del backend (NVIDIA Container Toolkit sull'host)
          </span>
        </div>
      ) : (
        <>
          <p className="page-subtitle">{gpus.length} GPU rilevate</p>
          {gpus.map((g) => {
            const usedPct = g.vram_total_mb > 0 ? Math.round((g.vram_used_mb / g.vram_total_mb) * 100) : 0;
            return (
              <div key={g.index} className="panel">
                <p style={{ fontWeight: 600, fontSize: 14 }}>
                  GPU {g.index}: {g.name}
                </p>
                <div className="form-row" style={{ marginTop: 8 }}>
                  <div className="form-field">
                    <label>vRAM</label>
                    <div>
                      {g.vram_used_mb} / {g.vram_total_mb} MB ({usedPct}%)
                    </div>
                  </div>
                  <div className="form-field">
                    <label>Temperatura</label>
                    <div>{fmt(g.temperature_c, " °C")}</div>
                  </div>
                  <div className="form-field">
                    <label>Utilizzo GPU</label>
                    <div>{fmt(g.utilization_percent, "%")}</div>
                  </div>
                  <div className="form-field">
                    <label>Potenza</label>
                    <div>
                      {g.power_draw_w ?? "—"} / {g.power_limit_w ?? "—"} W
                    </div>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-field">
                    <label>Driver</label>
                    <div>{fmt(g.driver_version)}</div>
                  </div>
                  <div className="form-field">
                    <label>Compute capability</label>
                    <div>{fmt(g.compute_capability)}</div>
                  </div>
                  <div className="form-field">
                    <label>PCI bus</label>
                    <div>{fmt(g.pci_bus_id)}</div>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-field">
                    <label>UUID</label>
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{fmt(g.uuid)}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
