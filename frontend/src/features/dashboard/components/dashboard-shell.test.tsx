import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { resetDashboardUiState } from "../state/dashboard-ui-store";
import { DashboardShell } from "./dashboard-shell";

const LIST_RESPONSE = {
  items: [
    {
      id: 11,
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
    },
  ],
  next_cursor: null,
};

const DETAIL_RESPONSE = {
  prisoner: {
    id: 11,
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
      provider: null,
      geo: {
        country_code: "US",
        asn: null,
      },
      reputation: {
        severity: null,
        confidence: null,
      },
      reason_metadata: {},
    },
  },
  protocol_history: [],
  credentials: [],
  commands: [],
  downloads: [],
};

class FakeWebSocket {
  private listeners: Record<string, Set<(event: unknown) => void>> = {
    open: new Set(),
    message: new Set(),
    close: new Set(),
  };

  addEventListener(type: string, listener: (event: unknown) => void) {
    this.listeners[type]?.add(listener);
  }

  removeEventListener(type: string, listener: (event: unknown) => void) {
    this.listeners[type]?.delete(listener);
  }

  close() {}

  emitClose() {
    this.listeners.close.forEach((listener) => listener({}));
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

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("DashboardShell", () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    resetDashboardUiState();
    queryClient = createQueryClient();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/prisoners/11")) {
        return Promise.resolve(
          new Response(JSON.stringify(DETAIL_RESPONSE), {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify(LIST_RESPONSE), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }),
      );
    }));
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

  function renderShell(options?: {
    forceMobileLayout?: boolean;
    realtimeEnabled?: boolean;
    websocketFactory?: (url: string) => FakeWebSocket;
  }) {
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <DashboardShell
            apiBaseUrl="https://api.holdingcell.test"
            websocketUrl="wss://api.holdingcell.test/ws/events"
            realtimeEnabled={options?.realtimeEnabled ?? false}
            websocketFactory={options?.websocketFactory}
            forceMobileLayout={options?.forceMobileLayout ?? false}
          />
        </QueryClientProvider>,
      );
    });
  }

  it("keeps connection status visible and does not auto-select a prisoner on first load", async () => {
    renderShell();
    await flush();

    const text = container.textContent ?? "";
    expect(text).toContain("Connection live");
    expect(text).toContain("Select a prisoner from the list");
    expect(container.querySelector(".dashboard-layout__content .detail-pane")).not.toBeNull();
  });

  it("renders command-strip chrome with inert placeholder navigation tabs", async () => {
    renderShell();
    await flush();

    const commandStrip = container.querySelector(".dashboard-shell__command-strip");
    expect(commandStrip).not.toBeNull();

    const nav = container.querySelector(".dashboard-shell__nav");
    expect(nav).not.toBeNull();

    const dashboardTab = container.querySelector('button[data-command-tab="dashboard"]');
    expect(dashboardTab?.getAttribute("aria-current")).toBe("page");

    const placeholderTabs = [
      container.querySelector('button[data-command-tab="realtime"]'),
      container.querySelector('button[data-command-tab="archive"]'),
      container.querySelector('button[data-command-tab="insights"]'),
    ];
    for (const tab of placeholderTabs) {
      expect(tab?.getAttribute("aria-disabled")).toBe("true");
      expect(tab?.getAttribute("tabindex")).toBe("-1");
    }

    expect(container.querySelector(".dashboard-shell__live-hero")).not.toBeNull();
  });

  it("uses unified command-band classes for kpi, filter, and connection surfaces", async () => {
    renderShell();
    await flush();

    const metricsBand = container.querySelector(".dashboard-shell__metrics-band");
    expect(metricsBand).not.toBeNull();

    const filtersBand = container.querySelector(".dashboard-shell__filters-band");
    expect(filtersBand).not.toBeNull();

    const tacticalLabels = [
      container.querySelector(".stats-bar__label.command-band__label"),
      container.querySelector(".filter-bar__label.command-band__label"),
      container.querySelector(".connection-pill__label.command-band__label"),
    ];
    for (const label of tacticalLabels) {
      expect(label).not.toBeNull();
    }

    const kpiReadout = container.querySelector(".stats-bar__value.command-band__readout");
    expect(kpiReadout).not.toBeNull();
  });

  it("applies shared command-center cohesion region hooks across primary shell regions", async () => {
    renderShell();
    await flush();

    expect(container.querySelector('[data-command-center-region="command-band"]')).not.toBeNull();
    expect(container.querySelector('[data-command-center-region="kpi-band"]')).not.toBeNull();
    expect(container.querySelector('[data-command-center-region="filter-band"]')).not.toBeNull();
    expect(container.querySelector('[data-command-center-region="live-list"]')).not.toBeNull();
    expect(container.querySelector('[data-command-center-region="dossier-pane"]')).not.toBeNull();

    expect(container.querySelector('[data-command-center-heading="shell-title"]')).not.toBeNull();
    expect(container.querySelector('[data-command-center-heading="panel-title"]')).not.toBeNull();
  });

  it("renders a framed cell-view layer in the live hero even before data density increases", async () => {
    renderShell();
    await flush();

    const cellView = container.querySelector('[data-command-center-region="cell-view"]');
    expect(cellView).not.toBeNull();
    expect(cellView?.classList.contains("dashboard-shell__cell-view")).toBe(true);
    expect(cellView?.querySelector(".dashboard-shell__cell-view-grid")).not.toBeNull();
    expect(cellView?.querySelector(".dashboard-shell__cell-view-status")).not.toBeNull();
  });

  it("uses mobile detail drawer behavior when forced into mobile layout", async () => {
    renderShell({ forceMobileLayout: true });
    await flush();
    const row = container.querySelector('[data-prisoner-id="11"]') as HTMLButtonElement;
    expect(row).not.toBeNull();

    act(() => {
      row.click();
    });
    await flush();

    expect(container.querySelector(".mobile-detail-drawer--open")).not.toBeNull();
  });

  it("shows stale reconnecting indicators and only enables retry once disconnected", async () => {
    const sockets: FakeWebSocket[] = [];
    const websocketFactory = vi.fn((_url: string) => {
      const socket = new FakeWebSocket();
      sockets.push(socket);
      return socket;
    });

    renderShell({ realtimeEnabled: true, websocketFactory });
    await flush();

    const retryButton = container.querySelector(".connection-pill__retry") as HTMLButtonElement;
    expect(retryButton.disabled).toBe(true);

    act(() => {
      sockets[0].emitClose();
    });
    await flush();

    expect(container.textContent).toContain("Connection reconnecting");
    expect(container.textContent).toContain("Live feed is stale");
    expect(retryButton.disabled).toBe(false);
  });
});
