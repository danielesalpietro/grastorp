# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo
file. Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il progetto aderisce a [Semantic Versioning](https://semver.org/lang/it/).

## [Unreleased]

### Added

- Persistenza dei deployment su SQLite (`backend/app/store.py`), al posto
  di uno store in memoria: i dati sopravvivono al riavvio del container.
  Ogni deployment è salvato come riga con il JSON del modello Pydantic,
  per evitare uno schema SQL parallelo mentre `ResourceConfig`/
  `NetworkConfig` sono ancora in evoluzione.
- Volume Docker dedicato (`grastorp-data`, montato su `/app/data`) nel
  `docker-compose.yml`; path del database configurabile via
  `GRASTORP_DB_PATH`.

## [0.1.0] - 2026-08-14

Primo rilascio: scaffold funzionante di backend e frontend.

### Added

- Backend FastAPI con gestione dei deployment e orchestrazione dei
  container tramite Docker SDK.
- Frontend React/Vite/TypeScript con Navigator a sidebar: **Host**
  (Manage/Monitor), **Deployments**, **Storage**, **Networking**, **GPU**.
- Sezione **Host → Manage**: informazioni reali su docker daemon e host
  (hostname, sistema operativo, kernel, architettura, CPU, RAM, versione
  Docker, container e immagini), lette direttamente dal docker daemon.
- Sezione **GPU**: rilevamento di tutte le GPU NVIDIA sull'host via
  `nvidia-smi` (vRAM used/total, temperatura, utilizzo, potenza, driver,
  compute capability, PCI bus, UUID), con fallback su un set minimo di
  campi per driver più datati.
- Catalogo statico di modelli Mixture-of-Experts da Hugging Face (Mixtral
  8x7B, Mixtral 8x22B, DeepSeek-MoE 16B).
- Wizard di deploy multi-step: selezione modello, framework (vLLM),
  modalità di calcolo **GPU** o **CPU Only**, risorse (CPU, RAM, GPU
  singola/multipla, limite vRAM, CPU offload), rete (IP di bind, porta
  API, NIC), WebUI opzionale.
- Avvio/arresto container di deployment tramite Docker SDK.
- Pagina di dettaglio deployment con tab Summary / Configuration / Monitor
  / Console.
- `docker-compose.yml` per l'esecuzione in sviluppo, con GPU reservation
  per il servizio backend (richiede NVIDIA Container Toolkit sull'host).
- Suite di test automatici: backend (`pytest`, API + logica di
  sanitizzazione CPU/GPU + parsing `nvidia-smi`) e frontend (`vitest` +
  React Testing Library, con test di non regressione sul toggle
  CPU Only/GPU e sulla struttura del Navigator).
- Workflow CI (GitHub Actions): test backend, type-check + test + build
  frontend, build delle immagini Docker su ogni push/PR.

### Known limitations

- **CPU Only mode** imposta i flag corretti ma l'immagine
  `vllm/vllm-openai` usata è compilata solo per CUDA: l'inferenza CPU
  reale non è ancora garantita — [#1](https://github.com/danielesalpietro/grastorp/issues/1).
- Framework alternativi a vLLM (TGI, llama.cpp) e le WebUI opzionali (Open
  WebUI, ecc.) sono stub non funzionanti.
- Rilevamento delle interfacce di rete dell'host non implementato.
- Storage/cache dei pesi dei modelli non implementato.
- Metriche di monitoraggio (host e per-deployment) e console/log streaming
  non implementati.
- Catalogo modelli statico, non collegato all'Hugging Face Hub API reale.
