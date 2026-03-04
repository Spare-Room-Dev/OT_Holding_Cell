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

function buildDetailResponse(prisoner: ListItem) {
  return {
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
      body: JSON.stringify(buildDetailResponse(prisoner)),
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

test.describe("@dashboard responsive shell", () => {
  test.beforeEach(async ({ page }) => {
    await installRealtimeSocketMock(page);
    await mockDashboardApi(page);
  });

  test("renders desktop list/detail composition with explicit analyst selection", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/");

    await expect(page.getByText("Connection live")).toBeVisible();
    await expect(
      page.getByText("Select a prisoner from the list to inspect attack summary and activity."),
    ).toBeVisible();
    await expect(page.locator(".dashboard-layout__content .detail-pane")).toBeVisible();
    await expect(page.locator(".mobile-detail-drawer--open")).toHaveCount(0);

    await page.locator('[data-prisoner-id="11"]').click();
    await expect(page.getByText("Source IP:")).toBeVisible();
    await expect(page.getByText("__RED_PHASE_FORCE_FAIL__")).toBeVisible();
  });

  test("opens a mobile detail drawer after row selection and supports close", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    await expect(page.locator(".dashboard-layout__content .detail-pane")).toHaveCount(0);
    await page.locator('[data-prisoner-id="11"]').click();
    await expect(page.locator(".mobile-detail-drawer--open")).toBeVisible();
    await expect(page.getByRole("dialog", { name: "Prisoner Detail" })).toBeVisible();

    await page.getByRole("button", { name: "Close" }).click();
    await expect(page.locator(".mobile-detail-drawer--open")).toHaveCount(0);
  });
});
