import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Storage } from "../Storage";
import { TasksProvider } from "../../context/TasksContext";

const LOCAL_DATASTORE = {
  id: "local",
  name: "Local Storage",
  type: "local",
  nfs_server: null,
  nfs_export_path: null,
  nfs_options: "rw,nfsvers=4",
  created_at: "2024-01-01T00:00:00+00:00",
};

const NFS_DATASTORE = {
  id: "ds-nfs",
  name: "NAS",
  type: "nfs",
  nfs_server: "10.0.0.5",
  nfs_export_path: "/export/grastorp",
  nfs_options: "rw,nfsvers=4",
  created_at: "2024-01-01T00:00:00+00:00",
};

const listDatastores = vi.fn().mockResolvedValue([LOCAL_DATASTORE]);
const createDatastore = vi.fn().mockResolvedValue(NFS_DATASTORE);
const deleteDatastore = vi.fn().mockResolvedValue(undefined);
const getLibraryConfig = vi.fn().mockResolvedValue({ datastore_id: "local" });
const setLibraryConfig = vi.fn().mockResolvedValue({ datastore_id: "ds-nfs" });

vi.mock("../../api/client", () => ({
  api: {
    listDatastores: (...args: unknown[]) => listDatastores(...args),
    createDatastore: (...args: unknown[]) => createDatastore(...args),
    deleteDatastore: (...args: unknown[]) => deleteDatastore(...args),
    getLibraryConfig: (...args: unknown[]) => getLibraryConfig(...args),
    setLibraryConfig: (...args: unknown[]) => setLibraryConfig(...args),
  },
}));

function renderPage() {
  return render(
    <TasksProvider>
      <Storage />
    </TasksProvider>
  );
}

describe("Storage", () => {
  it("elenca i datastore esistenti e la Model Library sul datastore configurato", async () => {
    renderPage();
    await screen.findByText("Local Storage");
    expect(screen.getByLabelText("Datastore della Library")).toHaveValue("local");
  });

  it("crea un datastore NFS", async () => {
    renderPage();
    await screen.findByText("Local Storage");

    fireEvent.click(screen.getByText("+ New Datastore"));
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "NAS" } });
    fireEvent.change(screen.getByText("Tipo").closest(".form-field")!.querySelector("select")!, {
      target: { value: "nfs" },
    });
    fireEvent.change(screen.getByPlaceholderText("10.0.0.5"), { target: { value: "10.0.0.5" } });
    fireEvent.change(screen.getByPlaceholderText("/export/grastorp"), { target: { value: "/export/grastorp" } });
    fireEvent.click(screen.getByText("Crea datastore"));

    await waitFor(() =>
      expect(createDatastore).toHaveBeenCalledWith(
        expect.objectContaining({ name: "NAS", type: "nfs", nfs_server: "10.0.0.5" })
      )
    );
  });

  it("cambia il datastore della Model Library", async () => {
    listDatastores.mockResolvedValueOnce([LOCAL_DATASTORE, NFS_DATASTORE]);
    renderPage();
    await screen.findByText("Local Storage");

    fireEvent.change(screen.getByLabelText("Datastore della Library"), { target: { value: "ds-nfs" } });

    await waitFor(() => expect(setLibraryConfig).toHaveBeenCalledWith({ datastore_id: "ds-nfs" }));
  });
});
