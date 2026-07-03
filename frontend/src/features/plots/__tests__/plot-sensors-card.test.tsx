import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { render } from "@/testing/test-utils";

import { PlotSensorsCard } from "../components/plot-sensors-card";

describe("PlotSensorsCard", () => {
  it("muestra la ultima lectura de cada sensor", async () => {
    render(<PlotSensorsCard plotId="p001" />);

    expect(screen.getByText("Cargando lecturas de sensores...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("42.3%")).toBeInTheDocument();
    });

    expect(screen.getByText("24.1°C")).toBeInTheDocument();
    expect(screen.getByText("20.5°C")).toBeInTheDocument();
    expect(screen.getByText("58.2%")).toBeInTheDocument();
  });
});
