# Logbook

Diario tecnico di avanzamento del progetto. A differenza del
[CHANGELOG.md](CHANGELOG.md), rivolto a chi usa il progetto, qui teniamo
traccia di decisioni architetturali, stato dei singoli componenti e prossimi
passi — utile a chi riprende il lavoro in un secondo momento.

## Stato attuale (2026-08-15)

| Componente                          | Stato |
|--------------------------------------|-------|
| Backend API (FastAPI)                | ✅ funzionante |
| Gestione container Docker (vLLM, GPU) | ✅ funzionante |
| Modalità CPU Only                    | ⚠️ flag corretti, immagine Docker non CPU-ready ([#1](https://github.com/danielesalpietro/grastorp/issues/1)) |
| Host → Manage (info host/docker)     | ✅ funzionante |
| Host → Monitor (metriche)            | 🚧 stub |
| GPU (rilevamento nvidia-smi)         | ✅ funzionante (1→N schede) |
| Deployments (wizard + gestione)      | ✅ funzionante per vLLM, modelli scelti tra i Template abilitati |
| Framework TGI / llama.cpp            | 🚧 stub; nessun vincolo formato↔framework ([#4](https://github.com/danielesalpietro/grastorp/issues/4)) |
| WebUI (Open WebUI, ecc.)             | 🚧 stub |
| Template (modello + registry Docker) | ✅ funzionante, CRUD + fetch caratteristiche da HF Hub |
| Model Library (download pesi)        | ⚠️ implementata e testata con mock, non ancora validata live ([dettagli](#2026-08-15--area-template-model-library-e-datastore)) |
| Datastore (locale/NFS/iSCSI)         | ✅ locale e NFS funzionanti, iSCSI stub; S3 solo progettato ([#6](https://github.com/danielesalpietro/grastorp/issues/6)) |
| Rilevamento NIC host                 | 🚧 stub |
| Test automatici + CI                 | ✅ pytest (backend), vitest+RTL (frontend), GitHub Actions |
| Persistenza deployment (SQLite)      | ✅ funzionante, dati su volume Docker |
| Persistenza template/datastore (JSON)| ✅ funzionante, file semplici in `backend/data/` |

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
- **Persistenza**: SQLite via il modulo `sqlite3` della stdlib, non
  SQLAlchemy/SQLModel — ogni deployment è una riga con il JSON del
  modello Pydantic in una colonna, invece di uno schema SQL a colonne
  separate. Scelta deliberata mentre `ResourceConfig`/`NetworkConfig`
  cambiano ancora spesso: evita migrazioni ad ogni campo aggiunto, al
  costo di non poter fare query SQL sui singoli campi (accettabile per i
  volumi in gioco). Una connessione sqlite3 per operazione (non
  condivisa tra thread) perché le route sono handler sync eseguiti nel
  threadpool di FastAPI. Verificato con un riavvio reale del processo
  (non solo mock) che i dati sopravvivono.
- **Persistenza template/datastore**: file JSON semplici
  (`template_store.py`, `datastore_store.py`, `library_config_store.py`),
  non SQLite — deliberatamente più semplice della persistenza dei
  deployment, perché questi modelli dati sono cambiati più volte nel giro
  di poche ore durante lo sviluppo (aggiunta di `enabled`, dei campi
  Library, rimozione di `volume_name`...). Da rivalutare insieme allo
  store dei deployment se in futuro serve interrogarli via query.
- **Model Library: un volume condiviso, non uno per modello**: la prima
  implementazione usava un volume Docker per repo_id
  (`grastorp-model-<repo>`); rivista dopo aver introdotto i Datastore,
  perché un volume-per-modello avrebbe richiesto pre-provisionare N
  export/sottocartelle NFS lato server. Un unico volume condiviso
  (`grastorp-library`) risolve il problema: i modelli convivono al suo
  interno come sottocartelle, usando la stessa struttura di cache che
  `huggingface_hub` adotterebbe da sé (`models--org--name/`), quindi non
  serve gestire il layout a mano. Le operazioni per singolo modello
  (verifica integrità, rimozione) restano scoped alla sua sottocartella
  (calcolata riproducendo la convenzione di naming di HF) senza toccare
  gli altri modelli nel volume.
- **Download nella Library via container helper, non nel processo
  backend**: il backend gira containerizzato con solo il socket Docker
  montato (stesso schema usato per avviare i container vLLM), quindi non
  ha accesso diretto al filesystem dell'host e non può scrivere lui
  stesso dentro un volume. Il download/verifica/rimozione avviene perciò
  in un container "helper" sibling (immagine `python:3.11-slim` con
  `huggingface_hub` installato al volo via pip, per non dover
  costruire/pubblicare un'immagine dedicata per ora), che il backend
  orchestra guardando stato e log via API Docker — mai eseguendo comandi
  sull'host direttamente.
- **Datastore, non configurazione diretta della Library**: la prima bozza
  metteva server/export NFS direttamente sulle impostazioni della Model
  Library. Rivista su richiesta esplicita per ricalcare l'architettura
  vSphere (datastore come concetto a sé, la Library — concettualmente un
  Content Library — vi risiede sopra): l'obiettivo dichiarato è farsi
  riconoscere da chi ragiona già per VM/datastore/content library in
  vSphere, non introdurre un vocabolario nuovo.
- **NFS via driver Docker nativo**: nessun plugin di terze parti — il
  driver `local` di Docker supporta NFS passando `driver_opts` (`type`,
  `o`, `device`) a `docker volume create`. iSCSI non ha un equivalente
  altrettanto diretto (richiederebbe gestione di initiator/LUN sull'host),
  dichiarato come stub e esplicitamente rifiutato in creazione finché non
  si implementa.

## Prossimi passi

1. Immagine vLLM CPU-ready per far funzionare davvero la modalità CPU Only
   ([#1](https://github.com/danielesalpietro/grastorp/issues/1)).
2. Validare la Model Library con un download reale end-to-end (host con
   Docker attivo e accesso a `huggingface.co`) e un mount NFS reale — non
   verificabile nell'ambiente di sviluppo usato finora.
3. Vincolare il framework al formato del modello (safetensors → vLLM,
   GGUF → llama.cpp), oggi selezionabili in combinazioni incoerenti
   ([#4](https://github.com/danielesalpietro/grastorp/issues/4)).
4. Check dello spazio libero sul datastore prima di avviare un download
   nella Library (oggi si può avviare anche senza spazio sufficiente, e
   fallisce a metà) + vista d'insieme dello spazio occupato.
5. S3 come storage tier-2 per i modelli scaricati e non in uso, con
   metadata di utilizzo (ultimo deployment associato, ultimo utilizzo) per
   distinguere modelli caldi/freddi ([#6](https://github.com/danielesalpietro/grastorp/issues/6)).
6. Rilevamento reale delle interfacce di rete dell'host.
7. Framework di inferenza alternativi (TGI, llama.cpp).
8. Metriche di monitoraggio host e per-deployment; console/log streaming.

## Log

### 2026-08-15 — Area Template, Model Library e Datastore

Giornata di lavoro più corposa, in più tappe:

1. **Area Template** (`/api/templates`): entità `Template` a due tipi
   (modello / registry Docker), CRUD completo, persistita su file JSON.
   I 3 modelli MoE del vecchio catalogo statico diventano template
   seminati di default; `hf_service.py`/`api/models.py` rimossi.
2. **Enable/disable + wizard**: flag `enabled` sul template; il
   `DeployWizard` sceglie il modello tra i template abilitati invece che
   dal catalogo statico; `deployments.py` valida contro questi.
3. **Caratteristiche da Hugging Face Hub**: `hf_metadata_service.py`
   interroga la REST API pubblica di HF per ricavare architettura,
   esperti, layer, parametri, sharding dato solo il `repo_id`
   (`POST /api/templates/from-hf`, `POST /api/templates/{id}/sync-hf`).
   Non verificabile live in questo ambiente di sviluppo: `huggingface.co`
   risulta esplicitamente bloccato dalla policy di rete del sandbox
   (`EGRESS_BLOCKED`, confermato sia con `curl` diretto sia con il tool di
   fetch); il servizio è scritto e testato con chiamate HTTP mockate.
4. **Model Library**: prima versione con un volume Docker per repo_id,
   poi rivista (vedi Decisioni tecniche) verso un **unico volume
   condiviso**, popolato da un container helper avviato via socket Docker
   (il backend containerizzato non ha accesso diretto al filesystem
   host). Download resumable via `huggingface_hub` (stessa cache che
   userebbe vLLM), verifica di integrità per nome+size dei file
   `.safetensors`, deployment bloccati se il modello non è pronto. Anche
   qui, nessun demone Docker attivo in questo ambiente (`docker info`
   fallisce: nessun `/var/run/docker.sock`) — tutti i test usano un
   client Docker fake, sullo stesso modello già in uso per
   `docker_service.py`.
5. **Datastore**: introdotti su richiesta esplicita per ricalcare
   l'architettura vSphere (datastore locale/NFS/iSCSI stub, Model Library
   come "Content Library" che vi risiede sopra), invece di configurare
   NFS direttamente sulla Library. Pagina Storage (era uno stub vuoto)
   ora la gestisce.
6. Aperte le issue [#4](https://github.com/danielesalpietro/grastorp/issues/4)
   (vincolo formato↔framework del modello) e
   [#6](https://github.com/danielesalpietro/grastorp/issues/6) (S3 come
   storage tier-2 per modelli scaricati e non in uso, con metadata
   caldo/freddo da progettare) per il lavoro di follow-up. Aperta la PR
   [#5](https://github.com/danielesalpietro/grastorp/pull/5).

Suite di test cresciuta da 43 a 84 casi lato backend (15 lato frontend)
nell'arco della giornata, mantenuta verde ad ogni tappa.

### 2026-08-14 — Persistenza SQLite

Sostituito lo store in-memory (`dict` a livello di modulo, perso ad ogni
riavvio) con SQLite (`backend/app/store.py`), su volume Docker dedicato.
Nessuna modifica al layer API: `store.py` espone le stesse funzioni di
prima, solo l'implementazione cambia. Aggiunto test di regressione che
verifica con una connessione sqlite3 indipendente che i dati finiscano
davvero su file, e uno smoke test manuale con riavvio reale del processo
uvicorn.

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
