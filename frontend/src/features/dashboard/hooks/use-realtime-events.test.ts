import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { dashboardQueryKeys } from "../data/query-keys";
import {
  getDashboardUiState,
  resetDashboardUiState,
  setDashboardCountryFilter,
  setDashboardSelectedPrisonerId,
} from "../state/dashboard-ui-store";
import {
  DASHBOARD_STATS_QUERY_KEY,
  applyRealtimeEnvelopeToCache,
  type DashboardRealtimeStatsSnapshot,
} from "../state/realtime-reconcile";
import type { DashboardPrisonerListResponse, DashboardPrisonerSummary } from "../types/contracts";
import type { DashboardRealtimeEnvelope } from "../types/realtime";
import { type UseRealtimeEventsResult, useRealtimeEvents } from "./use-realtime-events";

class FakeWebSocket {
  readonly url: string;
  closed = false;
  private listeners: Record<string, Set<(event: unknown) => void>> = {
    open: new Set(),
    message: new Set(),
    close: new Set(),
    error: new Set(),
  };

  constructor(url: string) {
    this.url = url;
  }

  addEventListener(type: string, listener: (event: unknown) => void): void {
    this.listeners[type]?.add(listener);
  }

  removeEventListener(type: string, listener: (event: unknown) => void): void {
    this.listeners[type]?.delete(listener);
  }

  close(): void {
    this.closed = true;
  }

  emitOpen(): void {
    this.listeners.open.forEach((listener) => listener({}));
  }

  emitClose(): void {
    this.listeners.close.forEach((listener) => listener({}));
  }

  emitMessage(payload: unknown): void {
    this.listeners.message.forEach((listener) =>
      listener({
        data: JSON.stringify(payload),
      }),
    );
  }
}

function buildPrisonerSummary(id: number, countryCode: string | null): DashboardPrisonerSummary {
  return {
    id,
    source_ip: `198.51.100.${id}`,
    country_code: countryCode,
    attempt_count: id * 2,
    first_seen_at: "2026-03-04T00:00:00Z",
    last_seen_at: "2026-03-04T00:10:00Z",
    credential_count: id,
    command_count: id + 1,
    download_count: 0,
    enrichment: {
      status: "pending",
      last_updated_at: null,
      country_code: countryCode,
      asn: null,
      reputation_severity: null,
    },
  };
}

function buildPrisonerEvent(
  event: "new_prisoner" | "prisoner_updated" | "prisoner_enriched",
  id: number,
  countryCode: string | null,
  attemptCount = 2,
): DashboardRealtimeEnvelope {
  return {
    event_id: `evt-${event}-${id}`,
    event,
    occurred_at: "2026-03-04T00:20:00Z",
    protocol_version: "1.0",
    payload: {
      ordering: {
        publish_sequence: id,
        source_updated_at: "2026-03-04T00:20:00Z",
      },
      prisoner_id: id,
      source_ip: `198.51.100.${id}`,
      country_code: countryCode,
      attempt_count: attemptCount,
      first_seen_at: "2026-03-04T00:00:00Z",
      last_seen_at: "2026-03-04T00:20:00Z",
      credential_count: 1,
      command_count: 1,
      download_count: 0,
      enrichment: {
        status: "pending",
        last_updated_at: null,
        country_code: countryCode,
        asn: null,
        reputation_severity: null,
      },
      detail_sync_stale: false,
      detail_last_changed_at: "2026-03-04T00:20:00Z",
    },
  };
}

function buildSyncCompleteEvent(syncId = "sync-1"): DashboardRealtimeEnvelope<"sync_complete"> {
  return {
    event_id: `evt-sync-complete-${syncId}`,
    event: "sync_complete",
    occurred_at: "2026-03-04T00:21:00Z",
    protocol_version: "1.0",
    payload: {
      ordering: {
        publish_sequence: 999,
        source_updated_at: "2026-03-04T00:21:00Z",
      },
      sync_id: syncId,
      estimated_total_chunks: 1,
    },
  };
}

function buildStatsEvent(total = 10): DashboardRealtimeEnvelope<"stats_update"> {
  return {
    event_id: `evt-stats-${total}`,
    event: "stats_update",
    occurred_at: "2026-03-04T00:22:00Z",
    protocol_version: "1.0",
    payload: {
      ordering: {
        publish_sequence: 1_000 + total,
        source_updated_at: "2026-03-04T00:22:00Z",
      },
      total_prisoners: total,
      active_prisoners: Math.max(0, total - 2),
      lifetime_attempts: total * 4,
      lifetime_credentials: total,
      lifetime_commands: total * 2,
      lifetime_downloads: total - 3,
      changed: true,
    },
  };
}

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderRealtimeHookProbe(
  queryClient: QueryClient,
  options: Parameters<typeof useRealtimeEvents>[0],
): { getLatest: () => UseRealtimeEventsResult; unmount: () => void } {
  let latest: UseRealtimeEventsResult | null = null;
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root: Root = createRoot(container);

  function Probe() {
    latest = useRealtimeEvents(options);
    return null;
  }

  act(() => {
    root.render(
      createElement(QueryClientProvider, { client: queryClient }, createElement(Probe)),
    );
  });

  return {
    getLatest: () => {
      if (latest === null) {
        throw new Error("Realtime hook probe has not produced a state snapshot yet");
      }
      return latest;
    },
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

describe("useRealtimeEvents + realtime reconcile", () => {
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-04T00:00:00Z"));
    resetDashboardUiState();
  });

  afterEach(() => {
    vi.useRealTimers();
    resetDashboardUiState();
    delete (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT;
  });

  it("reconciles prisoner/stats caches immutably across filtered list keys", () => {
    const queryClient = createTestQueryClient();
    const allKey = dashboardQueryKeys.prisoners.list({ country: null });
    const usKey = dashboardQueryKeys.prisoners.list({ country: "US" });
    const auKey = dashboardQueryKeys.prisoners.list({ country: "AU" });

    const allList: DashboardPrisonerListResponse = {
      items: [buildPrisonerSummary(1, "AU")],
      next_cursor: null,
    };
    const usList: DashboardPrisonerListResponse = {
      items: [],
      next_cursor: null,
    };
    const auList: DashboardPrisonerListResponse = {
      items: [buildPrisonerSummary(1, "AU")],
      next_cursor: null,
    };

    queryClient.setQueryData(allKey, allList);
    queryClient.setQueryData(usKey, usList);
    queryClient.setQueryData(auKey, auList);

    const previousAuReference = queryClient.getQueryData<DashboardPrisonerListResponse>(auKey);
    applyRealtimeEnvelopeToCache(queryClient, buildPrisonerEvent("new_prisoner", 2, "US", 7));
    applyRealtimeEnvelopeToCache(queryClient, buildStatsEvent(12));

    const updatedAll = queryClient.getQueryData<DashboardPrisonerListResponse>(allKey);
    const updatedUs = queryClient.getQueryData<DashboardPrisonerListResponse>(usKey);
    const updatedAu = queryClient.getQueryData<DashboardPrisonerListResponse>(auKey);
    const statsSnapshot = queryClient.getQueryData<DashboardRealtimeStatsSnapshot>(DASHBOARD_STATS_QUERY_KEY);

    expect(updatedAll?.items.some((item) => item.id === 2)).toBe(true);
    expect(updatedUs?.items.some((item) => item.id === 2)).toBe(true);
    expect(updatedAu).toBe(previousAuReference);
    expect(statsSnapshot).toMatchObject({
      total_prisoners: 12,
      lifetime_attempts: 48,
      changed: true,
    });
  });

  it("keeps stale reconnecting/offline state until sync completes", () => {
    const queryClient = createTestQueryClient();
    const sockets: FakeWebSocket[] = [];
    const websocketFactory = vi.fn((url: string) => {
      const socket = new FakeWebSocket(url);
      sockets.push(socket);
      return socket;
    });
    const probe = renderRealtimeHookProbe(queryClient, {
      websocketUrl: "wss://api.holdingcell.test/ws/events",
      websocketFactory,
      reconnectDelayMs: 1_000,
      offlineTimeoutMs: 2_000,
      now: () => Date.now(),
    });

    act(() => {
      sockets[0].emitClose();
    });
    expect(probe.getLatest().connectionStatus).toBe("reconnecting");
    expect(probe.getLatest().isStale).toBe(true);

    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(sockets).toHaveLength(2);

    act(() => {
      sockets[1].emitOpen();
    });
    expect(probe.getLatest().connectionStatus).toBe("reconnecting");
    expect(probe.getLatest().isStale).toBe(true);

    act(() => {
      vi.advanceTimersByTime(1_000);
    });
    expect(probe.getLatest().connectionStatus).toBe("offline");
    expect(probe.getLatest().isStale).toBe(true);

    act(() => {
      sockets[1].emitMessage(buildSyncCompleteEvent("sync-recovered"));
    });
    expect(probe.getLatest().connectionStatus).toBe("live");
    expect(probe.getLatest().isStale).toBe(false);

    probe.unmount();
  });

  it("exposes retry action that starts a fresh websocket session without clearing UI state", () => {
    const queryClient = createTestQueryClient();
    const listKey = dashboardQueryKeys.prisoners.list({ country: null });
    queryClient.setQueryData<DashboardPrisonerListResponse>(listKey, {
      items: [buildPrisonerSummary(42, "US")],
      next_cursor: null,
    });

    setDashboardSelectedPrisonerId(42);
    setDashboardCountryFilter("US");

    const sockets: FakeWebSocket[] = [];
    const websocketFactory = vi.fn((url: string) => {
      const socket = new FakeWebSocket(url);
      sockets.push(socket);
      return socket;
    });
    const probe = renderRealtimeHookProbe(queryClient, {
      websocketUrl: "wss://api.holdingcell.test/ws/events",
      websocketFactory,
      reconnectDelayMs: 60_000,
      offlineTimeoutMs: 5_000,
      now: () => Date.now(),
    });

    const beforeRetryUiState = getDashboardUiState();

    act(() => {
      sockets[0].emitClose();
    });
    expect(probe.getLatest().connectionStatus).toBe("reconnecting");

    act(() => {
      probe.getLatest().retryConnection();
    });

    expect(sockets).toHaveLength(2);
    expect(probe.getLatest().connectionStatus).toBe("reconnecting");
    expect(probe.getLatest().reconnectAttempt).toBeGreaterThanOrEqual(2);
    expect(getDashboardUiState()).toEqual(beforeRetryUiState);
    expect(queryClient.getQueryData(listKey)).toEqual({
      items: [buildPrisonerSummary(42, "US")],
      next_cursor: null,
    });

    probe.unmount();
  });
});
