import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Networking } from "../Networking";

vi.mock("../../api/client", () => ({
  api: {
    listNetworks: vi.fn().mockResolvedValue([
      {
        id: "abc123",
        name: "grastorp_default",
        driver: "bridge",
        scope: "local",
        subnet: "172.20.0.0/16",
        gateway: "172.20.0.1",
        internal: false,
        attachable: true,
        containers: ["grastorp-dep-1"],
      },
    ]),
    listNics: vi.fn().mockResolvedValue([]),
  },
}));

describe("Networking", () => {
  it("mostra le reti Docker rilevate come equivalente dei vSwitch ESXi", async () => {
    render(<Networking />);

    expect(await screen.findByText("grastorp_default")).toBeInTheDocument();
    expect(screen.getByText("bridge")).toBeInTheDocument();
    expect(screen.getByText("172.20.0.0/16")).toBeInTheDocument();
    expect(screen.getByText("grastorp-dep-1")).toBeInTheDocument();
  });
});
