# Studio di fattibilità: CLI per Grastorp (`grastorpcli`)

> Nota: questo documento è **solo uno studio di fattibilità**. Non introduce
> codice, non definisce un piano di implementazione impegnativo e non va
> interpretato come annuncio di una feature in arrivo. Serve a decidere *se*
> e *con quali prerequisiti* ha senso costruire una CLI per Grastorp.

## 1. Obiettivo

Valutare la fattibilità di una CLI di amministrazione per Grastorp,
ispirata a [`esxcli` e alle ESXi Shell
Commands](https://share.google/WOQ2lhUyq3rVNrZWP) di VMware: uno strumento
a riga di comando, eseguibile in locale sull'host o da remoto, che copra le
stesse aree gestite oggi dalla web GUI (host, GPU, storage, rete,
deployment, template, registry) con una sintassi a namespace gerarchici
tipo `esxcli <namespace> <oggetto> <comando>`.

Il confronto con `esxcli` è concettualmente calzante perché Grastorp si
descrive esso stesso come un "hypervisor" per modelli MoE (vedi README):
dove ESXi virtualizza macchine, Grastorp "virtualizza" deployment di
modelli come container. La stessa logica di namespace (`esxcli storage
core device list`, `esxcli network nic list`, `esxcli vm process list`) si
presta bene al dominio di Grastorp (`grastorpcli storage datastore list`,
`grastorpcli deployment list`, `grastorpcli gpu list`).

## 2. Metodo

Lo studio è basato sull'ispezione diretta del codice attuale (non su
supposizioni): router FastAPI in `backend/app/api/*.py`, schemi Pydantic in
`backend/app/schemas.py`, servizi in `backend/app/services/*.py`, oltre a
README, CHANGELOG e LOGBOOK. Una CLI di questo tipo avrebbe senso come
**client HTTP verso l'API REST già esistente** (`/api/*`), non come
strumento che duplica la logica di orchestrazione Docker: è lo stesso
pattern di `esxcli`, che è un client verso l'hostd/VMkernel API di ESXi.

## 3. Superficie API attuale (base per i namespace della CLI)

| Namespace CLI proposto | Endpoint REST esistenti | Stato di maturità |
|---|---|---|
| `host` | `GET /api/system/host` | ✅ Implementato e funzionante |
| `gpu` | `GET /api/system/gpus` | ✅ Implementato (via `nvidia-smi`) |
| `network nic` | `GET /api/system/nics` | ⚠️ Stub — ritorna lista vuota/placeholder, rilevamento reale non implementato |
| `deployment` | `GET/POST /api/deployments`, `GET/DELETE /api/deployments/{id}`, `POST .../start`, `POST .../stop` | ✅ CRUD e lifecycle completi per framework vLLM; altri framework sollevano `501 Not Implemented` |
| `template` | `GET/POST/PUT/DELETE /api/templates`, `POST .../from-registry`, `POST .../sync-registry` | ✅ CRUD completo, 2 tipi (model, docker_registry) |
| `template library` | `POST .../library/download`, `GET .../library`, `POST .../library/verify`, `DELETE .../library` | ✅ Implementato e testato (con Docker/HTTP mockati), **non ancora validato end-to-end** su host reale |
| `registry` | `GET/POST/PUT/DELETE /api/registries`, `GET .../search` | ✅ Implementato (provider Hugging Face + custom) |
| `storage datastore` | `GET/POST/DELETE /api/storage/datastores` | ✅ Implementato per tipo `local`/`nfs`; `iscsi` esplicitamente rifiutato (stub futuro) |
| `storage library-config` | `GET/PUT /api/storage/library/config` | ✅ Implementato |
| `framework` / `webui` (info) | `GET /api/system/frameworks`, `GET /api/system/webuis` | ✅ Implementato come cataloghi statici con flag `available` |
| `deployment console/logs` | *nessun endpoint* | ❌ Non esiste — nessun log streaming lato API |
| `deployment stats` / monitoring | *nessun endpoint* | ❌ Non esiste — nessuna metrica per-deployment o host esposta oltre a `host`/`gpu` |
| `network` (config bind/IP) | *nessun endpoint dedicato*, solo campo `network` dentro `DeploymentCreateRequest` | ⚠️ Parziale — la rete è configurata per-deployment, non gestita come risorsa host a sé |

Questa tabella è la base della fattibilità: **una CLI coprirebbe fedelmente
solo ciò che l'API già espone**. Le aree segnate ❌/⚠️ richiederebbero prima
lavoro sul backend, non solo sulla CLI.

## 4. Fattibilità per area

### 4.1 Host / GPU — **Alta fattibilità**
Endpoint stabili, sincroni, senza side-effect. Un `grastorpcli host info` o
`grastorpcli gpu list --format json` è implementabile subito come thin
wrapper su `GET /api/system/host` e `GET /api/system/gpus`. Nessun
prerequisito bloccante.

### 4.2 Deployment lifecycle — **Alta fattibilità, con limiti noti**
`list/create/start/stop/delete` mappano 1:1 sugli endpoint REST esistenti.
Il comando `create` dovrebbe accettare un file di configurazione (YAML/JSON,
come `esxcli` fa con opzioni posizionali estese) dato il numero di campi
annidati (`resources`, `network`, `offload`). Limiti da comunicare
all'utente della CLI, non da nascondere:
- solo framework `vllm` funziona davvero; `tgi`/`llama_cpp` restituiscono
  `501` (già gestito lato server, la CLI deve solo propagare l'errore in
  modo leggibile);
- nessun comando `console`/`logs` possibile finché non esiste un endpoint
  di streaming (vedi §5).

### 4.3 Template / Model Library — **Alta fattibilità, con avviso operativo**
CRUD template e comandi `library download/status/verify/remove` sono
implementabili 1:1. Va però segnalato chiaramente nella documentazione
della CLI (come fa già il README del progetto) che il download reale non è
stato validato end-to-end: un comando `grastorpcli template library
download` userebbe un percorso di codice testato solo con mock.

### 4.4 Registry — **Alta fattibilità**
CRUD + ricerca (`grastorpcli registry search <id> <query>`) mappano
direttamente sugli endpoint esistenti.

### 4.5 Storage / Datastore — **Alta fattibilità per `local`/`nfs`, non fattibile per `iscsi`**
Il tipo `iscsi` è dichiarato negli schemi ma la creazione lo rifiuta
esplicitamente (`ValueError`). Una CLI in stile `esxcli storage iscsi`
sarebbe fuorviante se implementata ora: meglio *non* esporre un
sotto-namespace `iscsi` finché il backend non lo supporta, per evitare che
la CLI prometta funzionalità che l'API rifiuta a runtime.

### 4.6 Network — **Bassa fattibilità allo stato attuale**
`GET /api/system/nics` è uno stub dichiarato (vedi commento nel codice
sorgente). Un namespace `grastorpcli network nic list` oggi ritornerebbe
dati vuoti o fasulli — esperienza peggiore che non avere il comando. Da
posticipare a dopo l'implementazione del rilevamento reale delle interfacce
di rete lato backend.

### 4.7 Monitoring / Console / Log streaming — **Non fattibile oggi**
Non esiste alcun endpoint per metriche di deployment, log o console
interattiva. Questa è l'area con il gap più simile a un vero uso "shell"
come `esxcli`/ESXi Shell (che permette anche accesso a processi VM e
log): per replicarla servirebbe innanzitutto:
- un endpoint di log streaming (es. `GET /api/deployments/{id}/logs` con
  Server-Sent Events o WebSocket, dato che Docker SDK espone già
  `container.logs(stream=True)`);
- un endpoint di metriche (`docker stats` equivalente) per CPU/RAM/GPU per
  container.

Senza questi, la CLI si limiterebbe a operazioni CRUD/lifecycle — utile ma
non equivalente a una vera "ESXi Shell".

## 5. Vincoli trasversali che condizionano il design della CLI

### 5.1 Assenza di autenticazione/autorizzazione — **blocco critico**
Il backend FastAPI (`backend/app/main.py`) non ha alcun meccanismo di auth:
CORS aperto a `*`, nessuna dipendenza `Depends()` di sicurezza su nessun
router, nessun token/API key richiesto su nessun endpoint (verificato per
grep su tutto `backend/app`). Questo è accettabile per una web GUI ad uso
locale in fase early-stage, ma per una **CLI amministrativa** pensata per
uso da remoto (come `esxcli` che opera via SSH/vCLI con credenziali) è un
prerequisito, non un dettaglio:
- una CLI che gira "in remoto" verso l'endpoint Grastorp senza auth
  significa che chiunque raggiunga la porta 8080 può creare/cancellare
  deployment, eliminare template, cancellare la Model Library o
  disabilitare/modificare registry — senza audit trail.
- prima di rilasciare una CLI "di produzione", andrebbe introdotto almeno
  un meccanismo minimo (API key statica via header, poi eventualmente
  token/OIDC), altrimenti la CLI amplifica un rischio già presente ma
  finora mitigato solo dall'uso "locale" implicito della GUI.

### 5.2 Stabilità dello schema dati
Il README dichiara esplicitamente che `templates.json`/`datastores.json`/
`library_config.json` sono scelte "deliberate ma da rivalutare" mentre i
modelli dati sono ancora in evoluzione. Una CLI pubblica come superficie
stabile (con retrocompatibilità attesa dagli utenti, come per `esxcli`)
rischia di dover rincorrere breaking change finché lo schema `Deployment`/
`Template` non si stabilizza. Non blocca lo studio, ma va tenuto in conto
nel versionamento della CLI (es. CLI versionata insieme al backend, non
indipendente).

### 5.3 Formato di output
`esxcli` supporta `--formatter=csv|xml|keyvalue` oltre alla tabella
default. Per Grastorp ha senso analogamente supportare almeno
`--format table|json`, dato che l'API è già JSON nativo (nessun lavoro di
serializzazione aggiuntivo, solo formattazione lato client).

### 5.4 Codici di uscita ed errori
Gli endpoint usano già codici HTTP semanticamente corretti (404, 409, 501,
502, 503) con `detail` testuale — buona base per mappare a exit code POSIX
distinti (es. 2 = not found, 3 = conflitto di stato, 4 = non implementato),
pattern simile a `esxcli` che distingue errori di validazione da errori di
sistema.

## 6. Proposta di design (solo per lo studio, non per l'implementazione)

- **Linguaggio/runtime**: Python con [Typer](https://typer.tiangolo.com/) o
  Click è la scelta più coerente: stesso linguaggio del backend, riuso
  potenziale degli schemi Pydantic già definiti in `schemas.py` per
  validazione lato client e per generare `--help` accurati senza
  duplicare la definizione dei campi.
- **Distribuzione**: pacchetto `pip install grastorpcli` separato dal
  backend (analogo al vCLI di VMware, distribuito indipendentemente da
  ESXi), configurabile con `GRASTORP_API_URL` (+ futura API key quando
  esisterà, vedi §5.1).
- **Struttura comandi** (esempio, non definitivo):
  ```
  grastorpcli host info
  grastorpcli gpu list [--format json]
  grastorpcli deployment list|create|start|stop|delete
  grastorpcli template list|create|sync-registry|library download|library status
  grastorpcli registry list|create|search
  grastorpcli storage datastore list|create|delete
  grastorpcli storage library-config get|set
  ```
- **Non esporre ancora**: `network nic *` (stub), `storage datastore
  iscsi` (rifiutato dal backend), `deployment console/logs` (nessun
  endpoint).

## 7. Conclusione

**La CLI è fattibile come client leggero sull'API REST già esistente**, per
circa i due terzi delle aree funzionali di Grastorp (host, GPU, deployment
lifecycle su vLLM, template, model library, registry, datastore
local/NFS). Il lavoro di implementazione vero e proprio sarebbe
contenuto, perché non richiede nuova logica di dominio: è essenzialmente
un client HTTP con parsing degli schemi già esistenti.

Due condizioni però la rendono prematura come *rilascio*, non come
prototipo interno:

1. **Assenza di autenticazione sul backend** (§5.1) — una CLI
   amministrativa remota su un'API completamente aperta è un rischio di
   sicurezza da chiudere prima, non dopo.
2. **Le parti più "shell-like" della metafora ESXi (console, log
   streaming, metriche live) non hanno ancora endpoint corrispondenti** —
   senza quelli, la CLI sarebbe un client CRUD, utile ma non la controparte
   di una vera ESXi Shell.

Raccomandazione: procedere con l'implementazione è ragionevole a piccoli
passi (host/GPU/deployment/template come primo scope, poiché già stabili e
testati), rimandando `network` e `storage iscsi` a quando i relativi
endpoint saranno reali, e trattando l'introduzione di un'API key/token come
prerequisito prima di qualunque uso della CLI al di fuori di un host
locale fidato.
