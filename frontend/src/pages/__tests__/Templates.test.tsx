import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Templates } from "../Templates";
import { TasksProvider } from "../../context/TasksContext";

const MODEL_TEMPLATE = {
  id: "t1",
  type: "model",
  name: "Mixtral 8x22B",
  description: "MoE su larga scala",
  spec: {
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

vi.mock("../../api/client", () => ({
  api: {
    listTemplates: (...args: unknown[]) => listTemplates(...args),
    createTemplate: (...args: unknown[]) => createTemplate(...args),
    deleteTemplate: (...args: unknown[]) => deleteTemplate(...args),
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
});
