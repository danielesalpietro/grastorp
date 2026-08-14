# Logbook

Diario tecnico di avanzamento del progetto. A differenza del
[CHANGELOG.md](CHANGELOG.md), rivolto a chi usa il progetto, qui teniamo
traccia di decisioni architetturali, stato dei singoli componenti e prossimi
passi — utile a chi riprende il lavoro in un secondo momento.

## Stato attuale (2026-08-14, v0.1.0)

| Componente                          | Stato |
|--------------------------------------|-------|
| Backend API (FastAPI)                | ✅ funzionante |
| Gestione container Docker (vLLM, GPU) | ✅ funzionante |
| Modalità CPU Only                    | ⚠️ flag corretti, immagine Docker non CPU-ready ([#1](https://github.com/danielesalpietro/grastorp/issues/1)) |
| Host → Manage (info host/docker)     | ✅ funzionante |
| Host → Monitor (metriche)            | 🚧 stub |
| GPU (rilevamento nvidia-smi)         | ✅ funzionante (1→N schede) |
| Deployments (wizard + gestione)      | ✅ funzionante per vLLM |
| Framework TGI / llama.cpp            | 🚧 stub |
| WebUI (Open WebUI, ecc.)             | 🚧 stub |
| Catalogo modelli HF                  | 🚧 statico, non collegato all'API reale |
| Storage / cache modelli              | 🚧 stub |
| Rilevamento NIC host                 | 🚧 stub |
| Test automatici + CI                 | ✅ pytest (backend), vitest+RTL (frontend), GitHub Actions |

## Decisioni tecniche

- **Orchestrazione**: un singolo host Docker (via socket montato), non
  Kubernetes — scelta per semplicità nella fase iniziale. Da rivalutare se
  emerge la necessità di più host.
- **Rilevamento GPU**: `nvidia-smi` eseguito dentro il container del
  backend, che richiede la NVIDIA Container Toolkit sull'host e una GPU
  device reservation nel `docker-compose.yml`. Alternativa scartata:
  parsing di `/proc`/`/sys` montati dall'host, più fragile e meno
  portabile di appoggiarsi a `nvidia-smi`.
- **Info host**: lette da `client.info()`/`client.version()` del docker
  daemon anziché dal container del backend, perché il daemon gira
  sull'host reale — i valori (CPU, RAM, hostname, kernel) riflettono la
  macchina fisica anche se Grastorp stesso è containerizzato. Questo
  meccanismo sparirà quando/se Grastorp diventerà un OS installabile
  bare-metal invece che un container.
- **`compute_mode` (CPU Only / GPU)**: campo esplicito su
  `ResourceConfig`, non derivato implicitamente da `gpu_indices` vuoto —
  per permettere alla UI di disabilitare esplicitamente i controlli GPU
  invece di dedurre lo stato. Il backend sanitizza comunque
  `gpu_indices`/`offload` lato server quando `compute_mode` è `cpu`,
  indipendentemente da cosa manda il client.
- **Layout UI**: Navigator a sidebar con sezioni (Host, Deployments,
  Storage, Networking, GPU) e pagine con pattern master/detail e tab
  (Summary/Configuration/Monitor/Console) — familiare a chi ha usato
  console di gestione hypervisor.
- **Test**: niente Docker/GPU/nvidia-smi reali nei test — `docker_service`
  e `gpu_service` sono testati mockando il client Docker e
  `subprocess`/`shutil.which`, così la suite gira ovunque (locale e CI)
  senza dipendenze hardware. Il job `docker-build` in CI fa solo `docker
  build` delle immagini (non `up`), perché il `docker-compose.yml`
  richiede una GPU reservation che i runner GitHub-hosted non hanno.

## Prossimi passi

1. Immagine vLLM CPU-ready per far funzionare davvero la modalità CPU Only
   ([#1](https://github.com/danielesalpietro/grastorp/issues/1)).
2. Collegare la ricerca modelli all'Hugging Face Hub API reale (oggi
   catalogo statico in `hf_service.py`).
3. Rilevamento reale delle interfacce di rete dell'host.
4. Framework di inferenza alternativi (TGI, llama.cpp).
5. Metriche di monitoraggio host e per-deployment; console/log streaming.
6. Storage/cache dei pesi dei modelli scaricati.

## Log

### 2026-08-14 — Test automatici e CI

Aggiunta suite di test di non regressione: `pytest` per il backend (API
deployments/models/system, sanitizzazione CPU/GPU, parsing `nvidia-smi`,
costruzione comando vLLM) e `vitest`+React Testing Library per il
frontend (toggle CPU Only/GPU nel wizard, struttura del Navigator).
Aggiunto workflow GitHub Actions (`.github/workflows/ci.yml`) che esegue
entrambe le suite più un build delle immagini Docker su ogni push/PR.

### 2026-08-14 — v0.1.0, primo rilascio

Scaffold iniziale di backend (FastAPI + Docker SDK) e frontend
(React/Vite). Aggiunte le sezioni Host (info reali su docker/host) e GPU
(rilevamento multi-scheda via `nvidia-smi`). Wizard di deploy con scelta
esplicita CPU Only / GPU. Aperta la issue #1 sulla modalità CPU Only.
Dettagli completi in [CHANGELOG.md](CHANGELOG.md).
