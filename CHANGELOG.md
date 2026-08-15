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
- **Area Template** (`/api/templates`, pagina Templates): entità `Template`
  con due tipi — modello (architettura, esperti, layer, parametri,
  sharding, context length, quantizzazione) e container pronto da registry
  Docker (immagine, RAM richiesta, requisiti GPU) — con CRUD completo,
  persistita su file JSON (`backend/app/template_store.py`). I 3 modelli
  MoE già noti sono seminati come template modello abilitati al primo
  avvio. Ogni template ha un flag `enabled`: il `DeployWizard` sceglie il
  modello tra i template abilitati (`type=model&enabled=true`) al posto
  del vecchio catalogo statico, rimosso insieme a `hf_service.py` e
  `api/models.py`.
- **Caratteristiche modello da Hugging Face Hub**
  (`backend/app/services/hf_metadata_service.py`): dato un `repo_id`,
  interroga la REST API pubblica di HF (config.json + elenco file) per
  ricavare architettura, esperti, layer, parametri e sharding. Nuovi
  endpoint `POST /api/templates/from-hf` (crea un template dal solo
  `repo_id`) e `POST /api/templates/{id}/sync-hf` (ri-sincronizza uno
  esistente).
- **Model Library condivisa**
  (`backend/app/services/model_library_service.py`): i pesi di un modello
  vengono scaricati una sola volta in un **unico volume Docker condiviso**
  (`grastorp-library`, non uno per modello), popolato tramite un
  container "helper" avviato via socket Docker — il backend containerizzato
  non ha accesso diretto al filesystem dell'host. Il download usa
  `huggingface_hub` con lo stesso formato di cache che userebbe vLLM, quindi
  un download interrotto riprende da dove si era fermato senza logica di
  resume custom. Endpoint su `/api/templates/{id}/library`: avvio/ripresa
  download, stato con percentuale di avanzamento (riallineato dal
  container reale), verifica di integrità (nome+size dei file
  `.safetensors` contro quanto riportato da HF), rimozione del singolo
  modello dal volume condiviso (senza toccare gli altri). I deployment
  vengono bloccati (409) se il modello richiesto è in download o in errore
  nella Library; se pronto, il volume viene montato **in sola lettura** nel
  container vLLM (`HF_HOME`), che quindi non lo riscarica.
- **Datastore** (`/api/storage/datastores`, pagina Storage — era uno stub
  vuoto): astrazione ispirata ai datastore vSphere, per far risiedere la
  Model Library su storage locale o condiviso. Tipi: `local` (sempre
  presente di default), `nfs` (via `driver_opts` nativi del driver `local`
  di Docker, nessun plugin di terze parti), `iscsi` dichiarato ma
  esplicitamente rifiutato in creazione come stub futuro. La Model Library
  usa il datastore scelto in `GET/PUT /api/storage/library/config`.

### Known limitations

- La Model Library e i Datastore NFS non sono stati validati con un
  download/mount reale in questo ciclo di sviluppo: l'ambiente usato non
  aveva accesso di rete a `huggingface.co` né un demone Docker attivo.
  Tutti i test coprono la logica con un client Docker fake e chiamate HTTP
  mockate — verificare su un host reale prima del rollout.
- Nessun vincolo ancora imposto tra formato del modello (safetensors vs
  GGUF) e framework di deploy compatibile: si può selezionare una
  combinazione incoerente e scoprirlo solo all'avvio del container
  ([#4](https://github.com/danielesalpietro/grastorp/issues/4)).
- S3 come storage tier-2 per i modelli scaricati e non più in uso è solo
  progettato, non implementato
  ([#6](https://github.com/danielesalpietro/grastorp/issues/6)).

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
