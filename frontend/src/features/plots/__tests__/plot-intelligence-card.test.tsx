import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { render } from "@/testing/test-utils";

import { PlotIntelligenceCard } from "../components/plot-intelligence-card";

describe("PlotIntelligenceCard", () => {
  it("muestra las recomendaciones ordenadas por prioridad real, no por orden de llegada", async () => {
    render(<PlotIntelligenceCard plotId="p001" />);

    await waitFor(() => {
      expect(screen.getByText("Anomalia de alta prioridad")).toBeInTheDocument();
    });

    const titles = screen.getAllByRole("heading", { level: 5 }).map((el) => el.textContent);

    expect(titles).toEqual(["Anomalia de alta prioridad", "Recomendacion de prioridad media"]);
  });

  it("muestra las parcelas analogas sin resolver un nombre real", async () => {
    const user = (await import("@/testing/test-utils")).userEvent.setup();
    render(<PlotIntelligenceCard plotId="p001" />);

    await user.click(screen.getByRole("button", { name: /Parcelas análogas/ }));

    await waitFor(() => {
      expect(screen.getByText("Parcela análoga #1")).toBeInTheDocument();
    });

    expect(screen.queryByText("other-user-plot-id")).not.toBeInTheDocument();
  });
});
