import { expect, test, type Page } from "@playwright/test";

type ListItem = {
  id: number;
  source_ip: string;
  country_code: string | null;
  attempt_count: number;
  first_seen_at: string;
  last_seen_at: string;
  credential_count: number;
  command_count: number;
  download_count: number;
  enrichment: {
    status: string;
    last_updated_at: string | null;
    country_code: string | null;
    asn: string | null;
    reputation_severity: string | null;
  };
};

function isoMinutesAgo(minutes: number): string {
  return new Date(Date.now() - minutes * 60_000).toISOString();
}

const PRISONERS: ListItem[] = [
  {
    id: 11,
    source_ip: "198.51.100.11",
    country_code: "US",
    attempt_count: 4,
    first_seen_at: isoMinutesAgo(20),
    last_seen_at: isoMinutesAgo(5),
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
];

function createSyncCompleteEnvelope() {
  const now = new Date().toISOString();
  return {
    event_id: "evt-sync-complete-1",
    event: "sync_complete",
    occurred_at: now,
    protocol_version: "1.0",
    payload: {
      ordering: {
        publish_sequence: 1,
        source_updated_at: now,
      },
      sync_id: "sync-1",
      estimated_total_chunks: 0,
    },
  };
}

async function installRealtimeSocketMock(page: Page) {
  await page.addInitScript(() => {
    class DashboardMockWebSocket {
      static instances: DashboardMockWebSocket[] = [];

      url: string;

      readyState = 0;

      private listeners: Record<string, Set<(event: unknown) => void>> = {
        open: new Set(),
        message: new Set(),
        close: new Set(),
      };

      constructor(url: string) {
        this.url = url;
        DashboardMockWebSocket.instances.push(this);
        queueMicrotask(() => {
          this.readyState = 1;
          this.dispatch("open", new Event("open"));
        });
      }

      addEventListener(type: string, listener: (event: unknown) => void) {
        this.listeners[type]?.add(listener);
      }

      removeEventListener(type: string, listener: (event: unknown) => void) {
        this.listeners[type]?.delete(listener);
      }

      close() {
        this.emitClose();
      }

      emitMessage(payload: unknown) {
        if (this.readyState === 3) {
          return;
        }
        this.dispatch(
          "message",
          new MessageEvent("message", {
            data: JSON.stringify(payload),
          }),
        );
      }

      emitClose() {
        if (this.readyState === 3) {
          return;
        }
        this.readyState = 3;
        this.dispatch("close", new Event("close"));
      }

      private dispatch(type: string, event: unknown) {
        this.listeners[type]?.forEach((listener) => listener(event));
      }
    }

    (window as Record<string, unknown>).__dashboardMockSockets = DashboardMockWebSocket.instances;
    (window as Record<string, unknown>).WebSocket = DashboardMockWebSocket;
  });
}

async function mockDashboardApi(page: Page) {
  await page.route(/\/api\/prisoners\/\d+$/, async (route) => {
    const id = Number(route.request().url().split("/").pop()?.split("?")[0]);
    const prisoner = PRISONERS.find((candidate) => candidate.id === id) ?? PRISONERS[0];

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        prisoner: {
          ...prisoner,
          enrichment: {
            status: prisoner.enrichment.status,
            last_updated_at: prisoner.enrichment.last_updated_at,
            provider: null,
            geo: {
              country_code: prisoner.enrichment.country_code,
              asn: prisoner.enrichment.asn,
            },
            reputation: {
              severity: prisoner.enrichment.reputation_severity,
              confidence: null,
            },
            reason_metadata: {},
          },
        },
        protocol_history: [],
        credentials: [],
        commands: [],
        downloads: [],
      }),
    });
  });

  await page.route(/\/api\/prisoners(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: PRISONERS,
        next_cursor: null,
      }),
    });
  });
}

async function emitSocketClose(page: Page) {
  await page.evaluate(() => {
    const sockets = (window as { __dashboardMockSockets?: Array<{ emitClose: () => void }> }).__dashboardMockSockets;
    if (!sockets || sockets.length === 0) {
      throw new Error("No dashboard mock socket instance is available");
    }
    sockets[sockets.length - 1].emitClose();
  });
}

async function emitSocketMessage(page: Page, payload: unknown) {
  await page.evaluate((eventPayload) => {
    const sockets =
      (window as { __dashboardMockSockets?: Array<{ emitMessage: (value: unknown) => void }> }).__dashboardMockSockets;
    if (!sockets || sockets.length === 0) {
      throw new Error("No dashboard mock socket instance is available");
    }
    sockets[sockets.length - 1].emitMessage(eventPayload);
  }, payload);
}

test.describe("@dashboard connection UX", () => {
  test.beforeEach(async ({ page }) => {
    await installRealtimeSocketMock(page);
    await mockDashboardApi(page);
  });

  test("surfaces reconnecting + stale state and supports manual retry recovery", async ({ page }) => {
    await page.goto("/");

    const retryButton = page.getByRole("button", { name: "Retry" });
    await expect(page.getByText("Connection live")).toBeVisible();
    await expect(retryButton).toBeDisabled();

    await emitSocketClose(page);
    await expect(page.getByText("Connection reconnecting")).toBeVisible();
    await expect(page.getByText("Live feed is stale while the connection is recovering.")).toBeVisible();
    await expect(retryButton).toBeEnabled();

    await retryButton.click();
    await expect(page.getByText("Reconnect attempts: 2")).toBeVisible();

    await emitSocketMessage(page, createSyncCompleteEnvelope());
    await expect(page.getByText("Connection live")).toBeVisible();
    await expect(page.getByText("Live feed is stale while the connection is recovering.")).toHaveCount(0);
    await expect(retryButton).toBeDisabled();
  });
});
