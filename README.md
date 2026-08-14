# grastorp

Hypervisor per Mixture-of-Experts: web GUI in stile ESXi per il deploy di modelli
MoE (es. Mixtral) come container, con framework di inferenza vLLM.

## Struttura

- `backend/` — API FastAPI. Gestisce i deployment e orchestra i container via
  Docker SDK (parla con il docker daemon dell'host tramite `/var/run/docker.sock`).
  - `app/services/docker_service.py` — avvio/arresto container (vLLM implementato,
    altri framework/WebUI stub).
  - `app/services/hf_service.py` — catalogo modelli MoE (stub: elenco statico,
    da sostituire con query reale all'HF Hub API).
  - `app/services/gpu_service.py` — rilevamento GPU (via `nvidia-smi` se presente)
    e NIC (stub, non implementato).
- `frontend/` — React + Vite + TypeScript. Layout a sidebar/topbar/recent-tasks
  in stile ESXi Host Client: elenco Deployments (= VM), wizard di creazione
  (= Create VM), pagina di configurazione con tab Summary/Configuration/Monitor/Console.

## Avvio (sviluppo, Docker)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8080 (docs su `/docs`)

Il backend monta il docker socket dell'host per poter avviare i container dei
modelli sullo stesso host Docker.

## Stato / stub

Al momento sono implementati solo: catalogo modelli MoE statico, deploy con
framework **vLLM**, gestione risorse CPU/RAM/GPU/offload, configurazione rete
(IP/porta). Sono stub (non ancora funzionanti): altri framework (TGI, llama.cpp),
WebUI (Open WebUI, ecc.), rilevamento NIC host, storage/cache modelli, metriche
di monitor, console/log streaming.

