import { useCallback, useEffect, useState } from "react";
import { api, Datastore, DatastoreCreateRequest, DatastoreType, LibraryConfig } from "../api/client";
import { useTasks } from "../context/TasksContext";

const TYPE_LABELS: Record<DatastoreType, string> = {
  local: "Locale",
  iscsi: "iSCSI",
  nfs: "NFS",
};

function defaultForm(): DatastoreCreateRequest {
  return { name: "", type: "local", nfs_server: "", nfs_export_path: "", nfs_options: "rw,nfsvers=4" };
}

export function Storage() {
  const [datastores, setDatastores] = useState<Datastore[]>([]);
  const [libraryConfig, setLibraryConfig] = useState<LibraryConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<DatastoreCreateRequest>(defaultForm());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savingLibrary, setSavingLibrary] = useState(false);
  const { pushTask } = useTasks();

  const reload = useCallback(() => {
    setLoading(true);
    Promise.all([api.listDatastores(), api.getLibraryConfig()])
      .then(([ds, lib]) => {
        setDatastores(ds);
        setLibraryConfig(lib);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(reload, [reload]);

  async function handleCreate() {
    setSubmitting(true);
    setError(null);
    try {
      await api.createDatastore(form);
      pushTask(`Datastore "${form.name}" creato`, "success");
      setForm(defaultForm());
      setShowForm(false);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(d: Datastore) {
    if (!confirm(`Eliminare il datastore "${d.name}"?`)) return;
    try {
      await api.deleteDatastore(d.id);
      pushTask(`Datastore "${d.name}" eliminato`, "success");
    } catch (e) {
      pushTask(`Eliminazione fallita: ${(e as Error).message}`, "error");
    }
    reload();
  }

  async function handleLibraryDatastoreChange(datastoreId: string) {
    setSavingLibrary(true);
    try {
      const updated = await api.setLibraryConfig({ datastore_id: datastoreId });
      setLibraryConfig(updated);
      pushTask("Datastore della Model Library aggiornato", "success");
    } catch (e) {
      pushTask(`Aggiornamento fallito: ${(e as Error).message}`, "error");
    } finally {
      setSavingLibrary(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Storage</h1>
      <p className="page-subtitle">Datastore disponibili per l'host e per la Model Library condivisa.</p>

      <div className="panel">
        <p style={{ fontWeight: 600, fontSize: 14 }}>Model Library</p>
        <p className="page-subtitle">
          I pesi dei modelli scaricati vengono salvati una sola volta in un volume condiviso, montato in sola
          lettura dai deployment che lo richiedono. Scegli su quale datastore risiede.
        </p>
        {loading || !libraryConfig ? (
          <p>Caricamento...</p>
        ) : (
          <div className="form-field" style={{ maxWidth: 320 }}>
            <label htmlFor="library-datastore">Datastore della Library</label>
            <select
              id="library-datastore"
              value={libraryConfig.datastore_id}
              disabled={savingLibrary}
              onChange={(e) => handleLibraryDatastoreChange(e.target.value)}
            >
              {datastores.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({TYPE_LABELS[d.type]})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="toolbar">
        <button className="btn btn--primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Annulla" : "+ New Datastore"}
        </button>
      </div>

      {showForm && (
        <div className="panel">
          <div className="form-row">
            <div className="form-field">
              <label htmlFor="ds-name">Nome</label>
              <input
                id="ds-name"
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="form-field">
              <label>Tipo</label>
              <select
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value as DatastoreType }))}
              >
                <option value="local">Locale (disco host)</option>
                <option value="nfs">NFS (mount point di rete)</option>
                <option value="iscsi" disabled>
                  iSCSI (LUN condivisa) — non ancora disponibile
                </option>
              </select>
            </div>
          </div>

          {form.type === "nfs" && (
            <div className="form-row">
              <div className="form-field">
                <label>Server NFS</label>
                <input
                  type="text"
                  placeholder="10.0.0.5"
                  value={form.nfs_server ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, nfs_server: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Export path</label>
                <input
                  type="text"
                  placeholder="/export/grastorp"
                  value={form.nfs_export_path ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, nfs_export_path: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Opzioni di mount</label>
                <input
                  type="text"
                  value={form.nfs_options ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, nfs_options: e.target.value }))}
                />
              </div>
            </div>
          )}

          {error && <div className="empty-state">{error}</div>}

          <div className="toolbar" style={{ marginTop: 8 }}>
            <button className="btn btn--primary" disabled={submitting || !form.name} onClick={handleCreate}>
              Crea datastore
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <p>Caricamento...</p>
      ) : (
        datastores.map((d) => (
          <div key={d.id} className="panel">
            <p style={{ fontWeight: 600, fontSize: 14 }}>
              {d.name} <span className="badge">{TYPE_LABELS[d.type]}</span>
              {libraryConfig?.datastore_id === d.id && <span className="badge badge--running">Model Library</span>}
            </p>
            {d.type === "nfs" && (
              <div className="form-row">
                <div className="form-field">
                  <label>Server</label>
                  <div>{d.nfs_server}</div>
                </div>
                <div className="form-field">
                  <label>Export path</label>
                  <div>{d.nfs_export_path}</div>
                </div>
                <div className="form-field">
                  <label>Opzioni</label>
                  <div>{d.nfs_options}</div>
                </div>
              </div>
            )}
            <div className="toolbar" style={{ marginTop: 8 }}>
              <button
                className="btn btn--danger"
                disabled={libraryConfig?.datastore_id === d.id}
                onClick={() => handleDelete(d)}
                title={libraryConfig?.datastore_id === d.id ? "In uso dalla Model Library" : undefined}
              >
                Elimina
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
