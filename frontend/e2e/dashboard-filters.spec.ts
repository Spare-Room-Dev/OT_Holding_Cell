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
    attempt_count: 6,
    first_seen_at: isoMinutesAgo(120),
    last_seen_at: isoMinutesAgo(6),
    credential_count: 1,
    command_count: 2,
    download_count: 0,
    enrichment: {
      status: "pending",
      last_updated_at: null,
      country_code: "US",
      asn: null,
      reputation_severity: null,
    },
  },
  {
    id: 12,
    source_ip: "198.51.100.12",
    country_code: "US",
    attempt_count: 2,
    first_seen_at: isoMinutesAgo(320),
    last_seen_at: isoMinutesAgo(130),
    credential_count: 0,
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
  {
    id: 33,
    source_ip: "203.0.113.33",
    country_code: "AU",
    attempt_count: 3,
    first_seen_at: isoMinutesAgo(90),
    last_seen_at: isoMinutesAgo(3),
    credential_count: 0,
    command_count: 1,
    download_count: 0,
    enrichment: {
      status: "pending",
      last_updated_at: null,
      country_code: "AU",
      asn: null,
      reputation_severity: null,
    },
  },
];

function createRealtimePrisonerEnvelope() {
  const now = new Date().toISOString();

  return {
    event_id: "evt-new-prisoner-44",
    event: "new_prisoner",
    occurred_at: now,
    protocol_version: "1.0",
    payload: {
      ordering: {
        publish_sequence: 44,
        source_updated_at: now,
      },
      prisoner_id: 44,
      source_ip: "203.0.113.44",
      country_code: "AU",
      attempt_count: 5,
      first_seen_at: isoMinutesAgo(4),
      last_seen_at: isoMinutesAgo(1),
      credential_count: 1,
      command_count: 1,
      download_count: 0,
      enrichment: {
        status: "pending",
        last_updated_at: null,
        country_code: "AU",
        asn: null,
        reputation_severity: null,
      },
      detail_sync_stale: false,
      detail_last_changed_at: now,
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
        if (this.readyState === 3) {
          return;
        }
        this.readyState = 3;
        this.dispatch("close", new Event("close"));
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

test.describe("@dashboard filters", () => {
  test.beforeEach(async ({ page }) => {
    await installRealtimeSocketMock(page);
    await mockDashboardApi(page);
  });

  test("applies country and time-window filters with realtime filtered-out updates", async ({ page }) => {
    await page.goto("/");

    const listSummary = page.locator(".prisoner-list .dashboard-panel__subtitle");
    await expect(page.locator(".prisoner-list.surface-panel.surface-panel--list.surface-panel--archive")).toBeVisible();
    await expect(listSummary).toContainText("Visible: 3");

    await page.getByLabel("Country").selectOption("US");
    await expect(listSummary).toContainText("Visible: 2 | Filtered out: 1");

    await page.getByLabel("Time window").selectOption("15m");
    await expect(listSummary).toContainText("Visible: 1 | Filtered out: 2");

    await emitSocketMessage(page, createRealtimePrisonerEnvelope());
    await expect(listSummary).toContainText("Visible: 1 | Filtered out: 3");
    await expect(page.locator(".filter-bar__meta")).toHaveText("Filtered out: 3");
    await expect(page.locator('[data-prisoner-id="11"]')).toHaveClass(/surface-card/);
  });
});
