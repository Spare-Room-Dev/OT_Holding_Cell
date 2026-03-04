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

  function renderShell(forceMobileLayout = false) {
    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <DashboardShell
            apiBaseUrl="https://api.holdingcell.test"
            websocketUrl="wss://api.holdingcell.test/ws/events"
            realtimeEnabled={false}
            forceMobileLayout={forceMobileLayout}
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

  it("uses mobile detail drawer behavior when forced into mobile layout", async () => {
    renderShell(true);
    await flush();
    const row = container.querySelector('[data-prisoner-id="11"]') as HTMLButtonElement;
    expect(row).not.toBeNull();

    act(() => {
      row.click();
    });
    await flush();

    expect(container.querySelector(".mobile-detail-drawer--open")).not.toBeNull();
  });
});
