import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { Templates } from "../Templates";
import { TasksProvider } from "../../context/TasksContext";

const HF_REGISTRY = {
  id: "huggingface",
  name: "Hugging Face",
  provider: "huggingface",
  base_url: "https://huggingface.co",
  api_key: null,
  enabled: true,
  created_at: "2024-01-01T00:00:00+00:00",
};

const MODEL_TEMPLATE = {
  id: "t1",
  type: "model",
  name: "Mixtral 8x22B",
  description: "MoE su larga scala",
  enabled: true,
  spec: {
    repo_id: "mistralai/Mixtral-8x22B-Instruct-v0.1",
    registry_id: "huggingface",
    architecture: "mixtral",
    num_experts: 8,
    num_experts_active: 2,
    num_layers: 56,
    params_billion: 141,
    shard_size_gb: 17.6,
    num_shards: 8,
    context_length: 65536,
    quantization: "fp16",
    library_status: "not_downloaded",
    library_progress_percent: null,
    library_error: null,
    downloaded_at: null,
  },
  created_at: "2026-01-01T00:00:00Z",
};

const READY_TEMPLATE = {
  ...MODEL_TEMPLATE,
  id: "t2",
  name: "DeepSeek-MoE 16B",
  spec: { ...MODEL_TEMPLATE.spec, library_status: "ready" },
};

const listTemplates = vi.fn().mockResolvedValue([MODEL_TEMPLATE]);
const createTemplate = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const deleteTemplate = vi.fn().mockResolvedValue(undefined);
const updateTemplate = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const createTemplateFromRegistry = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const syncTemplateFromRegistry = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const downloadToLibrary = vi.fn().mockResolvedValue({
  ...MODEL_TEMPLATE,
  spec: { ...MODEL_TEMPLATE.spec, library_status: "downloading", library_progress_percent: 0 },
});
const getLibraryStatus = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const verifyLibrary = vi.fn().mockResolvedValue(READY_TEMPLATE);
const deleteLibrary = vi.fn().mockResolvedValue({
  ...READY_TEMPLATE,
  spec: { ...READY_TEMPLATE.spec, library_status: "not_downloaded" },
});
const listRegistries = vi.fn().mockResolvedValue([HF_REGISTRY]);
const createRegistry = vi.fn().mockResolvedValue({ ...HF_REGISTRY, id: "r2", name: "Mirror" });
const updateRegistry = vi.fn().mockResolvedValue(HF_REGISTRY);
const deleteRegistry = vi.fn().mockResolvedValue(undefined);
const searchRegistryModels = vi.fn().mockResolvedValue([
  { repo_id: "deepseek-ai/deepseek-moe-16b-chat", downloads: 1234, likes: 42, pipeline_tag: "text-generation" },
]);

vi.mock("../../api/client", () => ({
  api: {
    listTemplates: (...args: unknown[]) => listTemplates(...args),
    createTemplate: (...args: unknown[]) => createTemplate(...args),
    deleteTemplate: (...args: unknown[]) => deleteTemplate(...args),
    updateTemplate: (...args: unknown[]) => updateTemplate(...args),
    createTemplateFromRegistry: (...args: unknown[]) => createTemplateFromRegistry(...args),
    syncTemplateFromRegistry: (...args: unknown[]) => syncTemplateFromRegistry(...args),
    downloadToLibrary: (...args: unknown[]) => downloadToLibrary(...args),
    getLibraryStatus: (...args: unknown[]) => getLibraryStatus(...args),
    verifyLibrary: (...args: unknown[]) => verifyLibrary(...args),
    deleteLibrary: (...args: unknown[]) => deleteLibrary(...args),
    listRegistries: (...args: unknown[]) => listRegistries(...args),
    createRegistry: (...args: unknown[]) => createRegistry(...args),
    updateRegistry: (...args: unknown[]) => updateRegistry(...args),
    deleteRegistry: (...args: unknown[]) => deleteRegistry(...args),
    searchRegistryModels: (...args: unknown[]) => searchRegistryModels(...args),
  },
}));

function renderPage() {
  return render(
    <TasksProvider>
      <Templates />
    </TasksProvider>
  );
}

describe("Templates", () => {
  it("elenca i template esistenti", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");
    expect(screen.getByText("mixtral")).toBeInTheDocument();
    expect(screen.getByText("141B")).toBeInTheDocument();
  });

  it("apre il form e crea un nuovo template", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");

    fireEvent.click(screen.getByText("+ New Template"));
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "DeepSeek MoE" } });
    fireEvent.click(screen.getByText("Crea template"));

    await waitFor(() => expect(createTemplate).toHaveBeenCalledWith(expect.objectContaining({ name: "DeepSeek MoE" })));
  });

  it("disabilita un template abilitato", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");

    fireEvent.click(screen.getByText("Disabilita"));

    await waitFor(() =>
      expect(updateTemplate).toHaveBeenCalledWith("t1", expect.objectContaining({ enabled: false }))
    );
  });

  it("sincronizza un template modello dal registry", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");

    fireEvent.click(screen.getByText("Sync da Registry"));

    await waitFor(() => expect(syncTemplateFromRegistry).toHaveBeenCalledWith("t1"));
  });

  it("cerca un modello in un registry e lo aggiunge come template", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");
    await screen.findByText("+ New Registry"); // segnale che i registry sono caricati

    fireEvent.change(screen.getByLabelText("Cerca"), { target: { value: "mixtral" } });
    fireEvent.click(screen.getByRole("button", { name: "Cerca" }));

    await screen.findByText("deepseek-ai/deepseek-moe-16b-chat");
    fireEvent.click(screen.getByText("Aggiungi come template"));

    await waitFor(() =>
      expect(createTemplateFromRegistry).toHaveBeenCalledWith({
        registry_id: "huggingface",
        repo_id: "deepseek-ai/deepseek-moe-16b-chat",
      })
    );
  });

  it("avvia il download in Library di un template non ancora scaricato", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");

    fireEvent.click(screen.getByText("Scarica in Library"));

    await waitFor(() => expect(downloadToLibrary).toHaveBeenCalledWith("t1"));
  });

  it("mostra verifica e rimozione per un template già in Library", async () => {
    listTemplates.mockResolvedValueOnce([READY_TEMPLATE]);
    renderPage();
    await screen.findByText("DeepSeek-MoE 16B");

    expect(screen.getByText("in Library")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Verifica integrità"));
    await waitFor(() => expect(verifyLibrary).toHaveBeenCalledWith("t2"));
  });

  it("il registry Hugging Face non può essere disabilitato né eliminato", async () => {
    renderPage();
    await screen.findByText("+ New Registry"); // segnale che i registry sono caricati

    const registryLabel = screen.getAllByText("Hugging Face").find((el) => el.tagName === "LABEL")!;
    const registryRow = registryLabel.closest(".form-row") as HTMLElement;
    expect(within(registryRow).getByLabelText("Abilitato")).toBeDisabled();
    expect(within(registryRow).getByRole("button", { name: "Elimina" })).toBeDisabled();
  });

  it("crea un registry custom", async () => {
    renderPage();
    await screen.findByText("+ New Registry");

    fireEvent.click(screen.getByText("+ New Registry"));
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Mirror" } });
    fireEvent.change(screen.getByLabelText("Base URL"), { target: { value: "https://mirror.example" } });
    fireEvent.click(screen.getByText("Crea registry"));

    await waitFor(() =>
      expect(createRegistry).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Mirror", base_url: "https://mirror.example" })
      )
    );
  });
});
