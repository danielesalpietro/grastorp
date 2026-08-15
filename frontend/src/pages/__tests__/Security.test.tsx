import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Security } from "../Security";

vi.mock("../../api/client", () => ({
  api: {
    getHostSecurity: vi.fn().mockResolvedValue({
      rootless: true,
      security_options: ["name=seccomp,profile=default", "name=rootless"],
      experimental: false,
      live_restore_enabled: false,
    }),
    listDeploymentSecurity: vi.fn().mockResolvedValue([
      {
        deployment_id: "dep-1",
        deployment_name: "mixtral-prod",
        container_id: "container-123",
        privileged: false,
        read_only_rootfs: true,
        user: "1000:1000",
        cap_add: [],
        cap_drop: ["ALL"],
        security_opt: ["no-new-privileges"],
        published_ports: ["0.0.0.0:8000->8000/tcp"],
      },
    ]),
  },
}));

describe("Security", () => {
  it("mostra il Security Profile dell'host e la postura di sicurezza dei deployment", async () => {
    render(<Security />);

    expect(await screen.findByText("attivo")).toBeInTheDocument();
    expect(screen.getByText(/name=rootless/)).toBeInTheDocument();

    expect(await screen.findByText("mixtral-prod")).toBeInTheDocument();
    expect(screen.getByText("ALL")).toBeInTheDocument();
    expect(screen.getByText("1000:1000")).toBeInTheDocument();
    expect(screen.getByText("0.0.0.0:8000->8000/tcp")).toBeInTheDocument();
  });
});
