import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardUiState, setDashboardCountryFilter } from "../state/dashboard-ui-store";
import { DashboardShell } from "../components/dashboard-shell";
import type { DashboardPrisonerRealtimePayload, DashboardRealtimeEnvelope } from "../types/realtime";

type RealtimePrisonerPayloadInput = Omit<DashboardPrisonerRealtimePayload, "ordering">;

const BASE_PRISONER: RealtimePrisonerPayloadInput = {
  prisoner_id: 11,
  source_ip: "198.51.100.11",
  country_code: "US",
  attempt_count: 4,
  first_seen_at: "2026-03-04T00:00:00Z",
  last_seen_at: "2026-03-04T00:10:00Z",
  credential_count: 1,
  command_count: 1,
  download_count: 0,
  enrichment: {
    status: "pending",
    last_updated_at: null,
    country_code: "US",
    asn: null,
    reputation_severity: null,
  },
  detail_sync_stale: false,
  detail_last_changed_at: "2026-03-04T00:10:00Z",
};

const LIST_RESPONSE = {
  items: [
    {
      id: BASE_PRISONER.prisoner_id,
      source_ip: BASE_PRISONER.source_ip,
      country_code: BASE_PRISONER.country_code,
      attempt_count: BASE_PRISONER.attempt_count,
      first_seen_at: BASE_PRISONER.first_seen_at,
      last_seen_at: BASE_PRISONER.last_seen_at,
      credential_count: BASE_PRISONER.credential_count,
      command_count: BASE_PRISONER.command_count,
      download_count: BASE_PRISONER.download_count,
      enrichment: {
        status: BASE_PRISONER.enrichment.status,
        last_updated_at: BASE_PRISONER.enrichment.last_updated_at,
        country_code: BASE_PRISONER.enrichment.country_code,
        asn: BASE_PRISONER.enrichment.asn,
        reputation_severity: BASE_PRISONER.enrichment.reputation_severity,
      },
    },
  ],
  next_cursor: null,
};

class FakeWebSocket {
  private listeners: Record<string, Set<(event: unknown) => void>> = {
    open: new Set(),
    message: new Set(),
    close: new Set(),
  };

  addEventListener(type: string, listener: (event: unknown) => void): void {
    this.listeners[type]?.add(listener);
  }

  removeEventListener(type: string, listener: (event: unknown) => void): void {
    this.listeners[type]?.delete(listener);
  }

  close(): void {}

  emitMessage(payload: DashboardRealtimeEnvelope): void {
    this.listeners.message.forEach((listener) =>
      listener({
        data: JSON.stringify(payload),
      }),
    );
  }
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function createRealtimeEnvelope(
  event: "new_prisoner" | "prisoner_enriched",
  payload: Partial<RealtimePrisonerPayloadInput>,
): DashboardRealtimeEnvelope {
  return {
    event_id: `evt-${event}-${payload.prisoner_id ?? BASE_PRISONER.prisoner_id}`,
    event,
    occurred_at: "2026-03-04T00:20:00Z",
    protocol_version: "1.0",
    payload: {
      ordering: {
        publish_sequence: payload.prisoner_id ?? BASE_PRISONER.prisoner_id,
        source_updated_at: "2026-03-04T00:20:00Z",
      },
      ...BASE_PRISONER,
      ...payload,
      enrichment: {
        ...BASE_PRISONER.enrichment,
        ...(payload.enrichment ?? {}),
      },
    },
  };
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("dashboard realtime integration", () => {
  let queryClient: QueryClient;
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    resetDashboardUiState();
    queryClient = createQueryClient();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);

    vi.stubGlobal("fetch", vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify(LIST_RESPONSE), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }),
      ),
    ));
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    queryClient.clear();
    vi.unstubAllGlobals();
    resetDashboardUiState();
    delete (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT;
  });

  it("reconciles realtime events through active filters and updates severity cues", async () => {
    const sockets: FakeWebSocket[] = [];
    const websocketFactory = vi.fn((_url: string) => {
      const socket = new FakeWebSocket();
      sockets.push(socket);
      return socket;
    });

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <DashboardShell
            apiBaseUrl="https://api.holdingcell.test"
            websocketUrl="wss://api.holdingcell.test/ws/events"
            websocketFactory={websocketFactory}
            realtimeEnabled
          />
        </QueryClientProvider>,
      );
    });
    await flush();

    const listPanel = container.querySelector(".prisoner-list.surface-panel.surface-panel--list.surface-panel--archive");
    const detailPanel = container.querySelector(".detail-pane.surface-panel.surface-panel--detail");
    expect(listPanel).not.toBeNull();
    expect(detailPanel).not.toBeNull();

    act(() => {
      setDashboardCountryFilter("US");
    });
    await flush();

    expect(container.textContent).toContain("Caution");

    act(() => {
      sockets[0].emitMessage(
        createRealtimeEnvelope("new_prisoner", {
          prisoner_id: 22,
          source_ip: "203.0.113.22",
          country_code: "AU",
          enrichment: {
            status: "pending",
            last_updated_at: null,
            country_code: "AU",
            asn: null,
            reputation_severity: null,
          },
        }),
      );
    });
    await flush();

    expect(container.textContent).toContain("Visible: 1 | Filtered out: 1");

    act(() => {
      sockets[0].emitMessage(
        createRealtimeEnvelope("prisoner_enriched", {
          prisoner_id: 11,
          attempt_count: 12,
          enrichment: {
            status: "complete",
            last_updated_at: "2026-03-04T00:22:00Z",
            country_code: "US",
            asn: "AS64000",
            reputation_severity: "high",
          },
        }),
      );
    });
    await flush();

    const text = container.textContent ?? "";
    expect(text).toContain("High");
    expect(text).toContain("Signal: escalate");
    expect(container.querySelector(".prisoner-row.surface-card.surface-card--row")).not.toBeNull();
    expect(container.querySelector(".prisoner-row__signal.surface-tactical-label")).not.toBeNull();
  });
});
