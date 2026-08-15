import { useEffect, useState } from "react";
import { api, DockerNetwork, NICDevice } from "../api/client";

export function Networking() {
  const [networks, setNetworks] = useState<DockerNetwork[] | null>(null);
  const [networksError, setNetworksError] = useState<string | null>(null);
  const [nics, setNics] = useState<NICDevice[]>([]);

  useEffect(() => {
    api
      .listNetworks()
      .then(setNetworks)
      .catch((e) => setNetworksError((e as Error).message));
    api.listNics().then(setNics);
  }, []);

  return (
    <div>
      <h1 className="page-title">Networking</h1>
      <p className="page-subtitle">
        Reti Docker dell'host — l'equivalente dei vSwitch/port group di ESXi: ogni rete raggruppa i container
        collegati e definisce un proprio subnet/gateway.
      </p>

      {networksError ? (
        <div className="empty-state">{networksError}</div>
      ) : networks === null ? (
        <p>Caricamento...</p>
      ) : networks.length === 0 ? (
        <div className="empty-state">Nessuna rete Docker rilevata.</div>
      ) : (
        <table className="grid">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Driver</th>
              <th>Scope</th>
              <th>Subnet</th>
              <th>Gateway</th>
              <th>Attachable</th>
              <th>Container collegati</th>
            </tr>
          </thead>
          <tbody>
            {networks.map((n) => (
              <tr key={n.id}>
                <td>
                  {n.name}
                  {n.internal ? <span className="badge badge--stopped">internal</span> : null}
                </td>
                <td>{n.driver}</td>
                <td>{n.scope}</td>
                <td>{n.subnet ?? "—"}</td>
                <td>{n.gateway ?? "—"}</td>
                <td>{n.attachable ? "Sì" : "No"}</td>
                <td>{n.containers.length > 0 ? n.containers.join(", ") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 style={{ fontSize: 14, fontWeight: 600, margin: "24px 0 4px" }}>NIC fisiche (uplink)</h2>
      <p className="page-subtitle">Interfacce di rete fisiche dell'host, l'equivalente degli uplink di un vSwitch.</p>
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
