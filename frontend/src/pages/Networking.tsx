import { useEffect, useState } from "react";
import { api, NICDevice } from "../api/client";

export function Networking() {
  const [nics, setNics] = useState<NICDevice[]>([]);

  useEffect(() => {
    api.listNics().then(setNics);
  }, []);

  return (
    <div>
      <h1 className="page-title">Networking</h1>
      <p className="page-subtitle">Interfacce di rete dell'host disponibili per i deployment.</p>
      {nics.length === 0 ? (
        <div className="empty-state">
          Nessuna NIC rilevata.
          <br />
          <span className="stub-note">Rilevamento NIC host non ancora implementato</span>
        </div>
      ) : (
        <table className="grid">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Indirizzo</th>
            </tr>
          </thead>
          <tbody>
            {nics.map((n) => (
              <tr key={n.name}>
                <td>{n.name}</td>
                <td>{n.address ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
