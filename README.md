# Grastorp

**Grastorp** è un hypervisor pensato per il deploy di modelli linguistici
Mixture-of-Experts (MoE) come container. Al posto di scegliere un sistema
operativo da installare su una macchina virtuale, scegli un modello — al
momento solo architetture MoE come Mixtral — e una web GUI ti guida nella
configurazione delle risorse (CPU, RAM, GPU, offload) e nel deploy come
container Docker, esposto tramite un endpoint API compatibile OpenAI.

> Stato: **early stage**. Il progetto è funzionante ma molte parti sono
> ancora stub — vedi la sezione [Stato del progetto](#stato-del-progetto) e
> le [Issue](../../issues) aperte.

## Perché

Distribuire un modello MoE oggi significa mettere insieme a mano container,
flag di framework, allocazione GPU, offload della memoria e reverse proxy.
Grastorp vuole rendere questo flusso un'operazione guidata da interfaccia
grafica, gestendo però parametri specifici per l'inferenza LLM (framework,
quantizzazione, offload, GPU multiple) invece che genericamente per macchine
virtuali.

## Funzionalità

- **Host**: informazioni reali sul docker daemon e sull'host che lo esegue
  (hostname, sistema operativo, kernel, CPU, RAM, versione Docker, container
  e immagini attivi).
- **GPU**: rilevamento di tutte le GPU NVIDIA presenti sull'host via
  `nvidia-smi` (vRAM, temperatura, utilizzo, potenza, driver, compute
  capability, PCI bus, UUID) — pensato per scalare da 1 a N schede.
- **Deployments**: wizard di creazione guidato — selezione del modello tra i
  Template modello abilitati, framework di inferenza, modalità **GPU** o
  **CPU Only**, risorse (CPU/RAM/GPU/offload), configurazione di rete (IP,
  porta, NIC) e WebUI opzionale.
- **Gestione container**: avvio e arresto dei deployment tramite Docker SDK,
  sullo stesso host Docker su cui gira Grastorp.
- **Templates**: catalogo di template riutilizzabili per il deploy, di due
  tipi — modello (architettura, esperti, layer, parametri, sharding, context
  length) e container pronto da registry Docker (immagine, RAM richiesta,
  requisiti GPU). Le caratteristiche di un template modello possono essere
  ricavate automaticamente da Hugging Face Hub dato solo il `repo_id`. Ogni
  template ha un flag enable/disable: solo i modelli abilitati compaiono nel
  wizard di deploy.
- **Model Library**: i pesi di un modello scaricato vengono salvati una sola
  volta in un volume condiviso (non uno per deployment), con ripresa
  automatica dei download interrotti e verifica di integrità dei file
  scaricati. I deployment montano la Library in sola lettura invece di
  riscaricare il modello ogni volta.
- **Storage / Datastore**: astrazione ispirata a vSphere — datastore locali
  (disco dell'host) o su mount NFS su cui far risiedere la Model Library
  (datastore iSCSI dichiarato in UI ma non ancora implementato).

## Stato del progetto

Funzionante oggi:

- Area **Template**: CRUD completo per template modello e registry Docker
  (`/api/templates`), 3 modelli MoE seminati di default e abilitati
  (Mixtral 8x7B/8x22B, DeepSeek-MoE 16B). Caratteristiche tecniche di un
  template modello ricavabili da Hugging Face Hub dato il `repo_id`
  (creazione o ri-sincronizzazione).
- **Model Library**: download dei pesi in un volume Docker condiviso
  (ripresa automatica se interrotto, verifica di integrità dei file),
  montato in sola lettura nei container di deploy. I deployment vengono
  bloccati se il modello richiesto è ancora in download o in errore nella
  Library. ⚠️ Implementata e coperta da test con Docker/HTTP mockati, ma
  non ancora validata con un download reale end-to-end (serve un host con
  Docker attivo e accesso a `huggingface.co`) — vedi CHANGELOG.
- **Datastore**: locale (sempre presente di default) o NFS, su cui può
  risiedere la Model Library.
- Deploy con framework **vLLM**, in modalità GPU (una o più schede, con
  CPU offload opzionale) o CPU Only.
- Gestione risorse (CPU, RAM, GPU) e rete (IP/porta) per ogni deployment.
- Persistenza dei deployment su SQLite, su volume Docker: sopravvivono al
  riavvio del container.

Ancora stub (segnaposto in UI, non funzionanti):

- Framework di inferenza alternativi (TGI, llama.cpp) — e nessun vincolo
  ancora imposto tra formato del modello (safetensors/GGUF) e framework
  compatibile ([#4](https://github.com/danielesalpietro/grastorp/issues/4)).
- WebUI opzionali affiancate all'API (Open WebUI, ecc.).
- Rilevamento delle interfacce di rete dell'host.
- Datastore iSCSI (dichiarato ma non ancora implementato) e S3 come storage
  tier-2 per i modelli scaricati e non in uso
  ([#6](https://github.com/danielesalpietro/grastorp/issues/6)).
- Metriche di monitoraggio (host e per-deployment) e console/log streaming.

Il dettaglio delle limitazioni note è tracciato nelle [Issue](../../issues)
del repository; l'andamento del lavoro è in [LOGBOOK.md](LOGBOOK.md).

## Architettura

```
backend/    API FastAPI — orchestrazione container via Docker SDK
frontend/   React + Vite + TypeScript — interfaccia web
```

- Il backend parla con il docker daemon dell'host tramite il socket montato
  (`/var/run/docker.sock`); le informazioni su host e GPU sono lette
  direttamente dal daemon e da `nvidia-smi`, non dal container del backend,
  così riflettono le risorse reali della macchina anche se Grastorp stesso
  gira containerizzato.
- Ogni deployment è un container separato che espone un endpoint API
  compatibile OpenAI sulla porta configurata.
- I deployment sono persistiti in un database SQLite su un volume Docker
  dedicato (`grastorp-data`, montato su `/app/data`); il path è
  configurabile con la variabile d'ambiente `GRASTORP_DB_PATH`.
- Template e datastore sono persistiti su file JSON semplici (non SQLite),
  in `backend/data/` (`templates.json`, `datastores.json`,
  `library_config.json`) — scelta deliberata per tenere bassa la
  complessità mentre questi modelli dati sono ancora in evoluzione; da
  rivalutare insieme allo store dei deployment se serve interrogarli.
- La **Model Library** vive in un unico volume Docker condiviso
  (`grastorp-library`), creato sul datastore configurato in Storage. Il
  backend, containerizzato con solo il socket Docker montato, non ha
  accesso diretto al filesystem dell'host: download, verifica integrità e
  rimozione di un modello avvengono perciò in un container "helper"
  (sibling, avviato via socket, stesso pattern usato per vLLM), orchestrato
  guardando stato e log via API Docker. Il download usa `huggingface_hub`
  con lo stesso formato di cache che userebbe vLLM, quindi un download
  interrotto riprende da dove si era fermato senza logica di resume
  custom.

## Requisiti

- Docker e Docker Compose.
- Per il rilevamento e l'uso delle GPU: driver NVIDIA + [NVIDIA Container
  Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  installati sull'host. Senza, Grastorp funziona comunque in modalità CPU
  Only ma non rileva GPU.
- Per la Model Library: l'host Docker deve poter raggiungere
  `huggingface.co` in uscita (download dei pesi) e, se si usa un datastore
  NFS, il pacchetto client NFS deve essere disponibile sull'host (il
  mount è gestito dal driver `local` nativo di Docker, nessun plugin).

## Avvio rapido

```bash
git clone https://github.com/danielesalpietro/grastorp.git
cd grastorp
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8080 (documentazione interattiva su `/docs`)

## Test

```bash
# backend
cd backend
pip install -r requirements-dev.txt
pytest

# frontend
cd frontend
npm install
npx tsc -b   # type check
npm test     # vitest
npm run build
```

La CI (GitHub Actions) esegue entrambe le suite più un build delle
immagini Docker su ogni push e pull request.

## Contribuire

Il progetto è agli inizi: issue e pull request sono benvenute, in particolare
sulle parti segnate come stub sopra. Le modifiche rilevanti vengono tracciate
in [CHANGELOG.md](CHANGELOG.md).
