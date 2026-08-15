import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Templates } from "../Templates";
import { TasksProvider } from "../../context/TasksContext";

const MODEL_TEMPLATE = {
  id: "t1",
  type: "model",
  name: "Mixtral 8x22B",
  description: "MoE su larga scala",
  enabled: true,
  spec: {
    repo_id: "mistralai/Mixtral-8x22B-Instruct-v0.1",
    architecture: "mixtral",
    num_experts: 8,
    num_experts_active: 2,
    num_layers: 56,
    params_billion: 141,
    shard_size_gb: 17.6,
    num_shards: 8,
    context_length: 65536,
    quantization: "fp16",
  },
  created_at: "2026-01-01T00:00:00Z",
};

const listTemplates = vi.fn().mockResolvedValue([MODEL_TEMPLATE]);
const createTemplate = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const deleteTemplate = vi.fn().mockResolvedValue(undefined);
const updateTemplate = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const createTemplateFromHF = vi.fn().mockResolvedValue(MODEL_TEMPLATE);
const syncTemplateFromHF = vi.fn().mockResolvedValue(MODEL_TEMPLATE);

vi.mock("../../api/client", () => ({
  api: {
    listTemplates: (...args: unknown[]) => listTemplates(...args),
    createTemplate: (...args: unknown[]) => createTemplate(...args),
    deleteTemplate: (...args: unknown[]) => deleteTemplate(...args),
    updateTemplate: (...args: unknown[]) => updateTemplate(...args),
    createTemplateFromHF: (...args: unknown[]) => createTemplateFromHF(...args),
    syncTemplateFromHF: (...args: unknown[]) => syncTemplateFromHF(...args),
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

  it("sincronizza un template modello da Hugging Face", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");

    fireEvent.click(screen.getByText("Sync da HF"));

    await waitFor(() => expect(syncTemplateFromHF).toHaveBeenCalledWith("t1"));
  });

  it("crea un template da Hugging Face inserendo il repo_id", async () => {
    renderPage();
    await screen.findByText("Mixtral 8x22B");

    fireEvent.change(screen.getByLabelText("Repo Hugging Face"), {
      target: { value: "deepseek-ai/deepseek-moe-16b-chat" },
    });
    fireEvent.click(screen.getByText("Crea da Hugging Face"));

    await waitFor(() =>
      expect(createTemplateFromHF).toHaveBeenCalledWith({ repo_id: "deepseek-ai/deepseek-moe-16b-chat" })
    );
  });
});
