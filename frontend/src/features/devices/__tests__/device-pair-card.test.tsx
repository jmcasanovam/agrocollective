import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { render, userEvent } from "@/testing/test-utils";
import { server } from "@/testing/mocks/server";

import { DevicePairCard } from "../components/device-pair-card";

describe("DevicePairCard", () => {
  it("muestra un mensaje especifico cuando la parcela ya tiene un dispositivo (409)", async () => {
    server.use(
      http.post("*/plots/:plotId/devices", () => {
        return HttpResponse.json(
          { detail: "Esta parcela ya tiene un dispositivo emparejado." },
          { status: 409 },
        );
      }),
    );

    const user = userEvent.setup();
    render(<DevicePairCard plotId="p001" plot={null} />);

    await user.click(screen.getByRole("button", { name: /Crear dispositivo/ }));

    await waitFor(() => {
      expect(
        screen.getByText("Esta parcela ya tiene un dispositivo emparejado."),
      ).toBeInTheDocument();
    });
  });

  it("registra el dispositivo cuando la parcela no tiene ninguno todavia", async () => {
    server.use(
      http.post("*/plots/:plotId/devices", () => {
        return HttpResponse.json(
          {
            id: "dev-001",
            plot_id: "p001",
            code: "AGRO-P-P001",
            is_active: true,
            last_seen_at: null,
            battery_mv: null,
            sensors: [],
          },
          { status: 201 },
        );
      }),
    );

    const user = userEvent.setup();
    render(<DevicePairCard plotId="p001" plot={null} />);

    await user.click(screen.getByRole("button", { name: /Crear dispositivo/ }));

    await waitFor(() => {
      expect(screen.getByText("Dispositivo registrado correctamente.")).toBeInTheDocument();
    });
  });
});
