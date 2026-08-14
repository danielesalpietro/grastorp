import { useEffect, useState } from "react";
import { api } from "../api/client";

export function TopBar() {
  const [dockerOk, setDockerOk] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => setDockerOk(h.docker))
      .catch(() => setDockerOk(false));
  }, []);

  return (
    <div className="topbar">
      <div className="topbar__brand">Grastorp — Hypervisor per Mixture-of-Experts</div>
      <div className="topbar__spacer" />
      <div className="topbar__meta">
        docker: {dockerOk === null ? "..." : dockerOk ? "connesso" : "non disponibile"}
      </div>
    </div>
  );
}
