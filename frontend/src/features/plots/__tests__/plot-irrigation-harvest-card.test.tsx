import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { render, userEvent } from "@/testing/test-utils";

import { PlotIrrigationHarvestCard } from "../components/plot-irrigation-harvest-card";

describe("PlotIrrigationHarvestCard", () => {
  it("lista los registros de riego y cosecha existentes", async () => {
    render(<PlotIrrigationHarvestCard plotId="p001" />);

    await waitFor(() => {
      expect(screen.getByText("12.5 mm")).toBeInTheDocument();
    });

    expect(screen.getByText("4200 kg/ha")).toBeInTheDocument();
  });

  it("registra un nuevo riego al enviar el formulario", async () => {
    const user = userEvent.setup();
    render(<PlotIrrigationHarvestCard plotId="p001" />);

    await waitFor(() => {
      expect(screen.getByText("12.5 mm")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Semana (inicio)"), "2026-07-06");
    await user.type(screen.getByLabelText("Volumen (mm)"), "15");
    await user.click(screen.getByRole("button", { name: "Registrar riego" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Volumen (mm)")).toHaveValue(null);
    });
  });
});
