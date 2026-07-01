import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { render } from "@/testing/test-utils";

import { PlotsList } from "../components/plots-list";

describe("PlotsList", () => {
  it("muestra las parcelas recibidas de la API", async () => {
    render(<PlotsList />);

    expect(screen.getByText("Cargando parcelas…")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Parcela 001")).toBeInTheDocument();
    });

    expect(screen.getByText("Parcela 002")).toBeInTheDocument();
    expect(screen.getByText("2 parcelas en total")).toBeInTheDocument();
  });
});
