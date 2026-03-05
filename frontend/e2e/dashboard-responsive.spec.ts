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

const COHESION_REGION_SELECTORS = [
  '[data-command-center-region="command-band"]',
  '[data-command-center-region="kpi-band"]',
  '[data-command-center-region="filter-band"]',
  '[data-command-center-region="live-list"]',
  '[data-command-center-region="dossier-pane"]',
];

type CohesionZoomLevel = "90%" | "100%" | "110%";

function buildDetailResponse(prisoner: ListItem) {
  return {
    prisoner: {
      ...prisoner,
      enrichment: {
        status: prisoner.enrichment.status,
        last_updated_at: prisoner.enrichment.last_updated_at,
        country_code: prisoner.enrichment.country_code,
        asn: prisoner.enrichment.asn,
        reputation_severity: prisoner.enrichment.reputation_severity,
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
  await page.route("**/api/prisoners**", async (route) => {
    const requestUrl = new URL(route.request().url());

    if (requestUrl.pathname === "/api/prisoners") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: PRISONERS,
          next_cursor: null,
        }),
      });
      return;
    }

    const match = requestUrl.pathname.match(/^\/api\/prisoners\/(\d+)$/);
    if (match) {
      const id = Number(match[1]);
      const prisoner = PRISONERS.find((candidate) => candidate.id === id) ?? PRISONERS[0];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(buildDetailResponse(prisoner)),
      });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not found" }),
    });
  });
}

async function assertNoClippingForCohesionRegions(page: Page) {
  const noClipDetected = await page.evaluate((selectors) => {
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (!element) {
        return false;
      }
      const rect = element.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) {
        return false;
      }
      if (rect.left >= window.innerWidth || rect.top >= window.innerHeight) {
        return false;
      }
    }
    return true;
  }, COHESION_REGION_SELECTORS);

  expect(noClipDetected).toBe(true);
}

async function assertDesktopZoomReadability(page: Page, zoomLevel: CohesionZoomLevel) {
  await page.evaluate((level) => {
    document.body.style.zoom = level;
  }, zoomLevel);

  for (const selector of COHESION_REGION_SELECTORS) {
    await expect(page.locator(selector)).toBeVisible();
  }

  await assertNoClippingForCohesionRegions(page);
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
    await expect(page.locator(".prisoner-list.surface-panel.surface-panel--list.surface-panel--archive")).toBeVisible();
    await expect(page.locator(".dashboard-layout__content .detail-pane")).toBeVisible();
    await expect(page.locator(".mobile-detail-drawer--open")).toHaveCount(0);
    await expect(page.locator('[data-command-center-region="command-band"]')).toBeVisible();
    await expect(page.locator('[data-command-center-region="kpi-band"]')).toBeVisible();
    await expect(page.locator('[data-command-center-region="filter-band"]')).toBeVisible();
    await expect(page.locator('[data-command-center-region="live-list"]')).toBeVisible();
    await expect(page.locator('[data-command-center-region="dossier-pane"]')).toBeVisible();
    await expect(page.locator('[data-command-center-heading="shell-title"]')).toBeVisible();
    await expect(page.locator('[data-command-center-heading="panel-title"]').first()).toBeVisible();

    await assertDesktopZoomReadability(page, "90%");
    await assertDesktopZoomReadability(page, "100%");
    await assertDesktopZoomReadability(page, "110%");
    await page.evaluate(() => {
      document.body.style.zoom = "100%";
    });

    await page.locator('[data-prisoner-id="11"]').click();
    const selectedRow = page.locator('[data-prisoner-id="11"]');
    await expect(selectedRow).toHaveAttribute("aria-pressed", "true");
    await expect(selectedRow).toHaveClass(/surface-card/);
    await expect(selectedRow).toHaveClass(/surface-card--row/);
    const detailPane = page.locator(".dashboard-layout__content .detail-pane");
    await expect(detailPane).toHaveClass(/surface-panel--detail/);
    await expect(detailPane.getByText("Source IP: 198.51.x.x")).toBeVisible();
    await expect(detailPane.getByText("198.51.100.11")).toHaveCount(0);
  });

  test("opens a mobile detail drawer after row selection and supports close", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    await expect(page.locator(".dashboard-layout__content .detail-pane")).toHaveCount(0);
    await expect(page.locator('[data-command-center-region="command-band"]')).toBeVisible();
    await expect(page.locator('[data-command-center-region="live-list"]')).toBeVisible();
    await page.locator('[data-prisoner-id="11"]').click();
    await expect(page.locator(".mobile-detail-drawer--open")).toBeVisible();
    await expect(page.getByRole("dialog", { name: "Prisoner Detail" })).toBeVisible();
    await expect(page.locator(".mobile-detail-drawer--open .detail-pane.surface-panel.surface-panel--detail")).toBeVisible();

    await page.locator(".mobile-detail-drawer__close").click();
    await expect(page.locator(".mobile-detail-drawer--open")).toHaveCount(0);
  });
});
