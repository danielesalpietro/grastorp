import { useCallback, useEffect, useState } from "react";
import {
  api,
  DockerRegistryTemplateSpec,
  LibraryStatus,
  ModelTemplateSpec,
  Template,
  TemplateCreateRequest,
  TemplateType,
} from "../api/client";
import { useTasks } from "../context/TasksContext";

const TYPE_LABELS: Record<TemplateType, string> = {
  model: "Modello",
  docker_registry: "Registry Docker",
};

const LIBRARY_BADGE: Record<LibraryStatus, string> = {
  not_downloaded: "stopped",
  downloading: "creating",
  ready: "running",
  error: "error",
};

const LIBRARY_LABEL: Record<LibraryStatus, string> = {
  not_downloaded: "non in Library",
  downloading: "download in corso",
  ready: "in Library",
  error: "errore Library",
};

function defaultModelSpec(): ModelTemplateSpec {
  return {
    repo_id: "",
    architecture: "",
    num_experts: null,
    num_experts_active: null,
    num_layers: null,
    params_billion: null,
    shard_size_gb: null,
    num_shards: null,
    context_length: null,
    quantization: null,
    volume_name: null,
    library_status: "not_downloaded",
    library_progress_percent: null,
    library_error: null,
    downloaded_at: null,
  };
}

function defaultDockerSpec(): DockerRegistryTemplateSpec {
  return {
    registry: "ghcr.io",
    image: "",
    tag: "latest",
    size_gb: null,
    ram_required_mb: null,
    gpu_required: false,
    gpu_compatible: [],
    min_vram_mb: null,
    cuda_version: null,
  };
}

function defaultForm(): TemplateCreateRequest {
  return { type: "model", name: "", description: "", enabled: true, spec: defaultModelSpec() };
}

function toCreateRequest(t: Template): TemplateCreateRequest {
  return { type: t.type, name: t.name, description: t.description, enabled: t.enabled, spec: t.spec };
}

function numOrNull(value: string): number | null {
  return value === "" ? null : Number(value);
}

export function Templates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [filter, setFilter] = useState<TemplateType | "all">("all");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<TemplateCreateRequest>(defaultForm());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hfRepoId, setHfRepoId] = useState("");
  const [hfSubmitting, setHfSubmitting] = useState(false);
  const [hfError, setHfError] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [libraryActionId, setLibraryActionId] = useState<string | null>(null);
  const { pushTask } = useTasks();

  const reload = useCallback(() => {
    setLoading(true);
    api
      .listTemplates(filter === "all" ? undefined : filter)
      .then(setTemplates)
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(reload, [reload]);

  useEffect(() => {
    const downloading = templates.filter(
      (t) => t.type === "model" && (t.spec as ModelTemplateSpec).library_status === "downloading"
    );
    if (downloading.length === 0) return;

    const interval = setInterval(() => {
      Promise.all(downloading.map((t) => api.getLibraryStatus(t.id))).then((updated) => {
        setTemplates((prev) => prev.map((t) => updated.find((u) => u.id === t.id) ?? t));
      });
    }, 3000);
    return () => clearInterval(interval);
  }, [templates]);

  function setType(type: TemplateType) {
    setForm({ ...defaultForm(), type, spec: type === "model" ? defaultModelSpec() : defaultDockerSpec() });
  }

  function updateModelSpec(patch: Partial<ModelTemplateSpec>) {
    setForm((f) => ({ ...f, spec: { ...(f.spec as ModelTemplateSpec), ...patch } }));
  }

  function updateDockerSpec(patch: Partial<DockerRegistryTemplateSpec>) {
    setForm((f) => ({ ...f, spec: { ...(f.spec as DockerRegistryTemplateSpec), ...patch } }));
  }

  async function handleCreate() {
    setSubmitting(true);
    setError(null);
    try {
      await api.createTemplate(form);
      pushTask(`Template "${form.name}" creato`, "success");
      setForm(defaultForm());
      setShowForm(false);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(t: Template) {
    if (!confirm(`Eliminare il template "${t.name}"?`)) return;
    try {
      await api.deleteTemplate(t.id);
      pushTask(`Template "${t.name}" eliminato`, "success");
    } catch (e) {
      pushTask(`Eliminazione fallita: ${(e as Error).message}`, "error");
    }
    reload();
  }

  async function handleToggleEnabled(t: Template) {
    try {
      await api.updateTemplate(t.id, { ...toCreateRequest(t), enabled: !t.enabled });
      pushTask(`Template "${t.name}" ${t.enabled ? "disabilitato" : "abilitato"}`, "success");
    } catch (e) {
      pushTask(`Operazione fallita: ${(e as Error).message}`, "error");
    }
    reload();
  }

  async function handleSyncHF(t: Template) {
    setSyncingId(t.id);
    try {
      await api.syncTemplateFromHF(t.id);
      pushTask(`Template "${t.name}" sincronizzato da Hugging Face`, "success");
    } catch (e) {
      pushTask(`Sync da HF fallito: ${(e as Error).message}`, "error");
    } finally {
      setSyncingId(null);
    }
    reload();
  }

  async function handleDownloadToLibrary(t: Template) {
    setLibraryActionId(t.id);
    try {
      const updated = await api.downloadToLibrary(t.id);
      setTemplates((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      pushTask(`Download di "${t.name}" avviato nella Library`, "success");
    } catch (e) {
      pushTask(`Download fallito: ${(e as Error).message}`, "error");
    } finally {
      setLibraryActionId(null);
    }
  }

  async function handleVerifyLibrary(t: Template) {
    setLibraryActionId(t.id);
    try {
      const updated = await api.verifyLibrary(t.id);
      setTemplates((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      pushTask(`Verifica integrità di "${t.name}" completata`, "success");
    } catch (e) {
      pushTask(`Verifica fallita: ${(e as Error).message}`, "error");
    } finally {
      setLibraryActionId(null);
    }
  }

  async function handleRemoveFromLibrary(t: Template) {
    if (!confirm(`Rimuovere "${t.name}" dalla Library? I pesi già scaricati verranno eliminati.`)) return;
    setLibraryActionId(t.id);
    try {
      const updated = await api.deleteLibrary(t.id);
      setTemplates((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
      pushTask(`"${t.name}" rimosso dalla Library`, "success");
    } catch (e) {
      pushTask(`Rimozione fallita: ${(e as Error).message}`, "error");
    } finally {
      setLibraryActionId(null);
    }
  }

  async function handleCreateFromHF() {
    setHfSubmitting(true);
    setHfError(null);
    try {
      await api.createTemplateFromHF({ repo_id: hfRepoId });
      pushTask(`Template creato da Hugging Face (${hfRepoId})`, "success");
      setHfRepoId("");
      reload();
    } catch (e) {
      setHfError((e as Error).message);
    } finally {
      setHfSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Templates</h1>
      <p className="page-subtitle">
        Cataloghi riutilizzabili per il deploy: caratteristiche dei modelli e container pronti da registry Docker.
      </p>

      <div className="toolbar">
        <button className={"btn" + (filter === "all" ? " btn--primary" : "")} onClick={() => setFilter("all")}>
          Tutti
        </button>
        <button className={"btn" + (filter === "model" ? " btn--primary" : "")} onClick={() => setFilter("model")}>
          Modello
        </button>
        <button
          className={"btn" + (filter === "docker_registry" ? " btn--primary" : "")}
          onClick={() => setFilter("docker_registry")}
        >
          Registry Docker
        </button>
        <button className="btn btn--primary" onClick={() => setShowForm((s) => !s)} style={{ marginLeft: "auto" }}>
          {showForm ? "Annulla" : "+ New Template"}
        </button>
      </div>

      <div className="panel">
        <p style={{ fontWeight: 600, fontSize: 14 }}>Crea template modello da Hugging Face</p>
        <p className="page-subtitle">
          Inserisci il repo_id: le caratteristiche tecniche (esperti, layer, parametri, shard...) vengono lette
          direttamente da Hugging Face Hub.
        </p>
        <div className="form-row">
          <div className="form-field">
            <label htmlFor="hf-repo-id">Repo Hugging Face</label>
            <input
              id="hf-repo-id"
              type="text"
              placeholder="mistralai/Mixtral-8x7B-Instruct-v0.1"
              value={hfRepoId}
              onChange={(e) => setHfRepoId(e.target.value)}
            />
          </div>
        </div>
        {hfError && <div className="empty-state">{hfError}</div>}
        <div className="toolbar" style={{ marginTop: 8 }}>
          <button className="btn btn--primary" disabled={hfSubmitting || !hfRepoId} onClick={handleCreateFromHF}>
            Crea da Hugging Face
          </button>
        </div>
      </div>

      {showForm && (
        <div className="panel">
          <div className="form-row">
            <div className="form-field">
              <label>Tipo</label>
              <select value={form.type} onChange={(e) => setType(e.target.value as TemplateType)}>
                <option value="model">Modello</option>
                <option value="docker_registry">Registry Docker</option>
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="tpl-name">Nome</label>
              <input
                id="tpl-name"
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-field">
              <label>Descrizione</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              />
            </div>
            <div className="form-field checkbox">
              <input
                id="tpl-enabled"
                type="checkbox"
                checked={form.enabled}
                onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
              />
              <label htmlFor="tpl-enabled">
                Abilitato <span className="stub-note">visibile nel wizard di deploy se abilitato</span>
              </label>
            </div>
          </div>

          {form.type === "model" ? (
            <>
              <div className="form-row">
                <div className="form-field">
                  <label>Repo Hugging Face</label>
                  <input
                    type="text"
                    value={(form.spec as ModelTemplateSpec).repo_id}
                    onChange={(e) => updateModelSpec({ repo_id: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Architettura</label>
                  <input
                    type="text"
                    value={(form.spec as ModelTemplateSpec).architecture}
                    onChange={(e) => updateModelSpec({ architecture: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Numero esperti</label>
                  <input
                    type="number"
                    value={(form.spec as ModelTemplateSpec).num_experts ?? ""}
                    onChange={(e) => updateModelSpec({ num_experts: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>Esperti attivi</label>
                  <input
                    type="number"
                    value={(form.spec as ModelTemplateSpec).num_experts_active ?? ""}
                    onChange={(e) => updateModelSpec({ num_experts_active: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>Layer</label>
                  <input
                    type="number"
                    value={(form.spec as ModelTemplateSpec).num_layers ?? ""}
                    onChange={(e) => updateModelSpec({ num_layers: numOrNull(e.target.value) })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-field">
                  <label>Parametri (miliardi)</label>
                  <input
                    type="number"
                    value={(form.spec as ModelTemplateSpec).params_billion ?? ""}
                    onChange={(e) => updateModelSpec({ params_billion: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>Dimensione shard (GB)</label>
                  <input
                    type="number"
                    value={(form.spec as ModelTemplateSpec).shard_size_gb ?? ""}
                    onChange={(e) => updateModelSpec({ shard_size_gb: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>Numero shard</label>
                  <input
                    type="number"
                    value={(form.spec as ModelTemplateSpec).num_shards ?? ""}
                    onChange={(e) => updateModelSpec({ num_shards: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>Context length</label>
                  <input
                    type="number"
                    value={(form.spec as ModelTemplateSpec).context_length ?? ""}
                    onChange={(e) => updateModelSpec({ context_length: numOrNull(e.target.value) })}
                  />
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="form-row">
                <div className="form-field">
                  <label>Registry</label>
                  <input
                    type="text"
                    value={(form.spec as DockerRegistryTemplateSpec).registry}
                    onChange={(e) => updateDockerSpec({ registry: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Immagine</label>
                  <input
                    type="text"
                    value={(form.spec as DockerRegistryTemplateSpec).image}
                    onChange={(e) => updateDockerSpec({ image: e.target.value })}
                  />
                </div>
                <div className="form-field">
                  <label>Tag</label>
                  <input
                    type="text"
                    value={(form.spec as DockerRegistryTemplateSpec).tag}
                    onChange={(e) => updateDockerSpec({ tag: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-field">
                  <label>Dimensione immagine (GB)</label>
                  <input
                    type="number"
                    value={(form.spec as DockerRegistryTemplateSpec).size_gb ?? ""}
                    onChange={(e) => updateDockerSpec({ size_gb: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>RAM richiesta (MB)</label>
                  <input
                    type="number"
                    value={(form.spec as DockerRegistryTemplateSpec).ram_required_mb ?? ""}
                    onChange={(e) => updateDockerSpec({ ram_required_mb: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>vRAM minima (MB)</label>
                  <input
                    type="number"
                    value={(form.spec as DockerRegistryTemplateSpec).min_vram_mb ?? ""}
                    onChange={(e) => updateDockerSpec({ min_vram_mb: numOrNull(e.target.value) })}
                  />
                </div>
                <div className="form-field">
                  <label>Versione CUDA</label>
                  <input
                    type="text"
                    value={(form.spec as DockerRegistryTemplateSpec).cuda_version ?? ""}
                    onChange={(e) => updateDockerSpec({ cuda_version: e.target.value || null })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-field checkbox">
                  <input
                    id="gpu_required"
                    type="checkbox"
                    checked={(form.spec as DockerRegistryTemplateSpec).gpu_required}
                    onChange={(e) => updateDockerSpec({ gpu_required: e.target.checked })}
                  />
                  <label htmlFor="gpu_required">Richiede GPU</label>
                </div>
                <div className="form-field">
                  <label>GPU compatibili (separate da virgola)</label>
                  <input
                    type="text"
                    value={(form.spec as DockerRegistryTemplateSpec).gpu_compatible.join(", ")}
                    onChange={(e) =>
                      updateDockerSpec({
                        gpu_compatible: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                </div>
              </div>
            </>
          )}

          {error && <div className="empty-state">{error}</div>}

          <div className="toolbar" style={{ marginTop: 8 }}>
            <button className="btn btn--primary" disabled={submitting || !form.name} onClick={handleCreate}>
              Crea template
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <p>Caricamento...</p>
      ) : templates.length === 0 ? (
        <div className="empty-state">Nessun template. Crea il primo con "New Template".</div>
      ) : (
        templates.map((t) => (
          <div key={t.id} className="panel">
            <p style={{ fontWeight: 600, fontSize: 14 }}>
              {t.name} <span className="badge">{TYPE_LABELS[t.type]}</span>{" "}
              <span className={`badge badge--${t.enabled ? "running" : "stopped"}`}>
                {t.enabled ? "abilitato" : "disabilitato"}
              </span>{" "}
              {t.type === "model" && (
                <span className={`badge badge--${LIBRARY_BADGE[(t.spec as ModelTemplateSpec).library_status]}`}>
                  {LIBRARY_LABEL[(t.spec as ModelTemplateSpec).library_status]}
                  {(t.spec as ModelTemplateSpec).library_status === "downloading" &&
                  (t.spec as ModelTemplateSpec).library_progress_percent != null
                    ? ` ${(t.spec as ModelTemplateSpec).library_progress_percent}%`
                    : ""}
                </span>
              )}
            </p>
            {t.description && <p className="page-subtitle">{t.description}</p>}
            {t.type === "model" && (t.spec as ModelTemplateSpec).library_error && (
              <p className="stub-note">{(t.spec as ModelTemplateSpec).library_error}</p>
            )}

            {t.type === "model" ? (
              <>
                <div className="form-row">
                  <div className="form-field">
                    <label>Repo Hugging Face</label>
                    <div>{(t.spec as ModelTemplateSpec).repo_id}</div>
                  </div>
                  <div className="form-field">
                    <label>Architettura</label>
                    <div>{(t.spec as ModelTemplateSpec).architecture}</div>
                  </div>
                  <div className="form-field">
                    <label>Esperti</label>
                    <div>
                      {(t.spec as ModelTemplateSpec).num_experts ?? "—"}
                      {(t.spec as ModelTemplateSpec).num_experts_active
                        ? ` (${(t.spec as ModelTemplateSpec).num_experts_active} attivi)`
                        : ""}
                    </div>
                  </div>
                  <div className="form-field">
                    <label>Layer</label>
                    <div>{(t.spec as ModelTemplateSpec).num_layers ?? "—"}</div>
                  </div>
                  <div className="form-field">
                    <label>Parametri</label>
                    <div>
                      {(t.spec as ModelTemplateSpec).params_billion != null
                        ? `${(t.spec as ModelTemplateSpec).params_billion}B`
                        : "—"}
                    </div>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-field">
                    <label>Shard</label>
                    <div>
                      {(t.spec as ModelTemplateSpec).num_shards ?? "—"} x{" "}
                      {(t.spec as ModelTemplateSpec).shard_size_gb ?? "—"} GB
                    </div>
                  </div>
                  <div className="form-field">
                    <label>Context length</label>
                    <div>{(t.spec as ModelTemplateSpec).context_length ?? "—"}</div>
                  </div>
                  <div className="form-field">
                    <label>Quantizzazione</label>
                    <div>{(t.spec as ModelTemplateSpec).quantization ?? "—"}</div>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="form-row">
                  <div className="form-field">
                    <label>Immagine</label>
                    <div>
                      {(t.spec as DockerRegistryTemplateSpec).registry}/{(t.spec as DockerRegistryTemplateSpec).image}
                      :{(t.spec as DockerRegistryTemplateSpec).tag}
                    </div>
                  </div>
                  <div className="form-field">
                    <label>Dimensione</label>
                    <div>{(t.spec as DockerRegistryTemplateSpec).size_gb ?? "—"} GB</div>
                  </div>
                  <div className="form-field">
                    <label>RAM richiesta</label>
                    <div>{(t.spec as DockerRegistryTemplateSpec).ram_required_mb ?? "—"} MB</div>
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-field">
                    <label>GPU</label>
                    <div>
                      {(t.spec as DockerRegistryTemplateSpec).gpu_required
                        ? `richiesta (min. ${(t.spec as DockerRegistryTemplateSpec).min_vram_mb ?? "—"} MB vRAM)`
                        : "non richiesta"}
                    </div>
                  </div>
                  <div className="form-field">
                    <label>GPU compatibili</label>
                    <div>{(t.spec as DockerRegistryTemplateSpec).gpu_compatible.join(", ") || "—"}</div>
                  </div>
                  <div className="form-field">
                    <label>CUDA</label>
                    <div>{(t.spec as DockerRegistryTemplateSpec).cuda_version ?? "—"}</div>
                  </div>
                </div>
              </>
            )}

            <div className="toolbar" style={{ marginTop: 8 }}>
              <button className="btn" onClick={() => handleToggleEnabled(t)}>
                {t.enabled ? "Disabilita" : "Abilita"}
              </button>
              {t.type === "model" && (
                <button className="btn" disabled={syncingId === t.id} onClick={() => handleSyncHF(t)}>
                  {syncingId === t.id ? "Sync in corso..." : "Sync da HF"}
                </button>
              )}
              {t.type === "model" &&
                (() => {
                  const libraryStatus = (t.spec as ModelTemplateSpec).library_status;
                  const busy = libraryActionId === t.id;
                  if (libraryStatus === "not_downloaded") {
                    return (
                      <button className="btn" disabled={busy} onClick={() => handleDownloadToLibrary(t)}>
                        {busy ? "Avvio..." : "Scarica in Library"}
                      </button>
                    );
                  }
                  if (libraryStatus === "error") {
                    return (
                      <>
                        <button className="btn" disabled={busy} onClick={() => handleDownloadToLibrary(t)}>
                          {busy ? "Avvio..." : "Riprova download"}
                        </button>
                        <button className="btn" disabled={busy} onClick={() => handleRemoveFromLibrary(t)}>
                          Rimuovi dalla Library
                        </button>
                      </>
                    );
                  }
                  if (libraryStatus === "ready") {
                    return (
                      <>
                        <button className="btn" disabled={busy} onClick={() => handleVerifyLibrary(t)}>
                          {busy ? "Verifica..." : "Verifica integrità"}
                        </button>
                        <button className="btn" disabled={busy} onClick={() => handleRemoveFromLibrary(t)}>
                          Rimuovi dalla Library
                        </button>
                      </>
                    );
                  }
                  return null;
                })()}
              <button className="btn btn--danger" onClick={() => handleDelete(t)}>
                Elimina
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
