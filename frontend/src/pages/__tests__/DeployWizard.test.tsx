import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeployWizard } from "../DeployWizard";
import { TasksProvider } from "../../context/TasksContext";

vi.mock("../../api/client", () => ({
  api: {
    listModels: vi.fn().mockResolvedValue([
      {
        repo_id: "mistralai/Mixtral-8x7B-Instruct-v0.1",
        display_name: "Mixtral 8x7B Instruct",
        architecture: "moe",
        num_experts: 8,
        params_billion: 46.7,
        description: "",
      },
    ]),
    listGpus: vi.fn().mockResolvedValue([
      {
        index: 0,
        name: "RTX 3090",
        vram_total_mb: 24576,
        vram_used_mb: 0,
        vram_free_mb: 24576,
        driver_version: null,
        uuid: null,
        pci_bus_id: null,
        temperature_c: null,
        utilization_percent: null,
        power_draw_w: null,
        power_limit_w: null,
        compute_capability: null,
      },
    ]),
    listNics: vi.fn().mockResolvedValue([]),
    listFrameworks: vi.fn().mockResolvedValue([{ id: "vllm", label: "vLLM", available: true }]),
    listWebuis: vi.fn().mockResolvedValue([{ id: "none", label: "Nessuna (solo API)", available: true }]),
    createDeployment: vi.fn(),
  },
}));

function renderWizard() {
  return render(
    <MemoryRouter>
      <TasksProvider>
        <DeployWizard />
      </TasksProvider>
    </MemoryRouter>
  );
}

async function goToRisorseStep() {
  await screen.findByText("Mixtral 8x7B Instruct");
  fireEvent.click(screen.getByText("Mixtral 8x7B Instruct"));
  fireEvent.click(screen.getByText("Avanti")); // Modello -> Framework
  fireEvent.click(screen.getByText("Avanti")); // Framework -> Risorse
}

describe("DeployWizard - modalità di calcolo GPU / CPU Only", () => {
  it("di default è in modalità GPU con i controlli GPU/offload abilitati", async () => {
    renderWizard();
    await goToRisorseStep();

    expect(screen.getByLabelText("GPU")).toBeChecked();
    expect(screen.getByLabelText(/GPU 0: RTX 3090/)).not.toBeDisabled();
    expect(screen.getByLabelText(/Abilita CPU offload/)).not.toBeDisabled();
  });

  it("passando a CPU Only disabilita la selezione GPU e il CPU offload", async () => {
    renderWizard();
    await goToRisorseStep();

    fireEvent.click(screen.getByLabelText("CPU Only"));

    expect(screen.getByLabelText(/GPU 0: RTX 3090/)).toBeDisabled();
    expect(screen.getByLabelText(/Abilita CPU offload/)).toBeDisabled();
  });

  it("deseleziona la GPU scelta quando si passa a CPU Only", async () => {
    renderWizard();
    await goToRisorseStep();

    fireEvent.click(screen.getByLabelText(/GPU 0: RTX 3090/));
    expect(screen.getByLabelText(/GPU 0: RTX 3090/)).toBeChecked();

    fireEvent.click(screen.getByLabelText("CPU Only"));
    expect(screen.getByLabelText(/GPU 0: RTX 3090/)).not.toBeChecked();
  });

  it("tornando a GPU riabilita i controlli", async () => {
    renderWizard();
    await goToRisorseStep();

    fireEvent.click(screen.getByLabelText("CPU Only"));
    fireEvent.click(screen.getByLabelText("GPU"));

    expect(screen.getByLabelText(/GPU 0: RTX 3090/)).not.toBeDisabled();
    expect(screen.getByLabelText(/Abilita CPU offload/)).not.toBeDisabled();
  });
});
