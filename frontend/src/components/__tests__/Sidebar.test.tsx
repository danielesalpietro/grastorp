import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "../Sidebar";

describe("Sidebar", () => {
  it("mostra Host con le sotto-voci Manage e Monitor, e le altre sezioni del Navigator", () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText("Host")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage" })).toHaveAttribute("href", "/host/manage");
    expect(screen.getByRole("link", { name: "Monitor" })).toHaveAttribute("href", "/host/monitor");
    expect(screen.getByRole("link", { name: "Deployments" })).toHaveAttribute("href", "/deployments");
    expect(screen.getByRole("link", { name: "Storage" })).toHaveAttribute("href", "/storage");
    expect(screen.getByRole("link", { name: "Networking" })).toHaveAttribute("href", "/networking");
    expect(screen.getByRole("link", { name: "GPU" })).toHaveAttribute("href", "/gpu");
    expect(screen.getByRole("link", { name: "Templates" })).toHaveAttribute("href", "/templates");
  });
});
