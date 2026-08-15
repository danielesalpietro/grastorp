import { useEffect, useState } from "react";
import { api, ContainerSecurity, HostSecurityProfile } from "../api/client";

export function Security() {
  const [profile, setProfile] = useState<HostSecurityProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [deployments, setDeployments] = useState<ContainerSecurity[] | null>(null);
  const [deploymentsError, setDeploymentsError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getHostSecurity()
      .then(setProfile)
      .catch((e) => setProfileError((e as Error).message));
    api
      .listDeploymentSecurity()
      .then(setDeployments)
      .catch((e) => setDeploymentsError((e as Error).message));
  }, []);

  return (
    <div>
      <h1 className="page-title">Security</h1>
      <p className="page-subtitle">
        Postura di sicurezza del docker daemon e dei deployment — l'equivalente del Security Profile ESXi
        (lockdown mode, firewall, permessi per-VM).
      </p>

      <h2 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 8px" }}>Security Profile dell'host</h2>
      {profileError ? (
        <div className="empty-state">{profileError}</div>
      ) : profile === null ? (
        <p>Caricamento...</p>
      ) : (
        <div className="panel">
          <div className="form-row">
            <div className="form-field">
              <label>Rootless (≈ Lockdown Mode)</label>
              <div>
                <span className={"badge " + (profile.rootless ? "badge--running" : "badge--stopped")}>
                  {profile.rootless ? "attivo" : "non attivo"}
                </span>
              </div>
            </div>
            <div className="form-field">
              <label>Live restore</label>
              <div>{profile.live_restore_enabled ? "Sì" : "No"}</div>
            </div>
            <div className="form-field">
              <label>Build sperimentale</label>
              <div>{profile.experimental ? "Sì" : "No"}</div>
            </div>
          </div>
          <div className="form-row">
            <div className="form-field">
              <label>Meccanismi di isolamento attivi (seccomp/AppArmor/SELinux)</label>
              <div>
                {profile.security_options.length > 0 ? profile.security_options.join(", ") : "nessuno riportato"}
              </div>
            </div>
          </div>
        </div>
      )}

      <h2 style={{ fontSize: 14, fontWeight: 600, margin: "24px 0 8px" }}>Postura di sicurezza per deployment</h2>
      <p className="page-subtitle">
        L'equivalente delle impostazioni di sicurezza per-VM in ESXi: capability Linux, rootfs, utente e porte
        pubblicate di ciascun container.
      </p>
      {deploymentsError ? (
        <div className="empty-state">{deploymentsError}</div>
      ) : deployments === null ? (
        <p>Caricamento...</p>
      ) : deployments.length === 0 ? (
        <div className="empty-state">Nessun deployment presente.</div>
      ) : (
        <table className="grid">
          <thead>
            <tr>
              <th>Deployment</th>
              <th>Privileged</th>
              <th>Rootfs read-only</th>
              <th>Utente</th>
              <th>Cap. aggiunte</th>
              <th>Cap. rimosse</th>
              <th>Security opt</th>
              <th>Porte pubblicate</th>
            </tr>
          </thead>
          <tbody>
            {deployments.map((d) => (
              <tr key={d.deployment_id}>
                <td>{d.deployment_name}</td>
                <td>
                  {d.container_id ? (
                    <span className={"badge " + (d.privileged ? "badge--error" : "badge--running")}>
                      {d.privileged ? "sì" : "no"}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td>{d.container_id ? (d.read_only_rootfs ? "Sì" : "No") : "—"}</td>
                <td>{d.user ?? (d.container_id ? "root (default)" : "—")}</td>
                <td>{d.cap_add.length > 0 ? d.cap_add.join(", ") : "—"}</td>
                <td>{d.cap_drop.length > 0 ? d.cap_drop.join(", ") : "—"}</td>
                <td>{d.security_opt.length > 0 ? d.security_opt.join(", ") : "—"}</td>
                <td>{d.published_ports.length > 0 ? d.published_ports.join(", ") : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
