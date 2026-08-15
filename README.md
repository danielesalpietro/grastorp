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
- **Deployments**: wizard di creazione guidato — selezione del modello MoE,
  framework di inferenza, modalità **GPU** o **CPU Only**, risorse
  (CPU/RAM/GPU/offload), configurazione di rete (IP, porta, NIC) e WebUI
  opzionale.
- **Gestione container**: avvio e arresto dei deployment tramite Docker SDK,
  sullo stesso host Docker su cui gira Grastorp.

## Stato del progetto

Funzionante oggi:

- Catalogo statico di modelli MoE (Mixtral 8x7B/8x22B, DeepSeek-MoE 16B).
- Deploy con framework **vLLM**, in modalità GPU (una o più schede, con
  CPU offload opzionale) o CPU Only.
- Gestione risorse (CPU, RAM, GPU) e rete (IP/porta) per ogni deployment.
- Persistenza dei deployment su SQLite, su volume Docker: sopravvivono al
  riavvio del container.

Ancora stub (segnaposto in UI, non funzionanti):

- Framework di inferenza alternativi (TGI, llama.cpp).
- WebUI opzionali affiancate all'API (Open WebUI, ecc.).
- Rilevamento delle interfacce di rete dell'host.
- Storage/cache dei pesi dei modelli.
- Metriche di monitoraggio (host e per-deployment) e console/log streaming.
- Ricerca modelli collegata all'Hugging Face Hub reale (oggi è un elenco
  statico).

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

## Requisiti

- Docker e Docker Compose.
- Per il rilevamento e l'uso delle GPU: driver NVIDIA + [NVIDIA Container
  Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  installati sull'host. Senza, Grastorp funziona comunque in modalità CPU
  Only ma non rileva GPU.

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
