import type { QueryClient, QueryKey } from "@tanstack/react-query";
import { dashboardQueryKeys } from "../data/query-keys";
import type { DashboardPrisonerListResponse, DashboardPrisonerSummary } from "../types/contracts";
import type {
  DashboardPrisonerRealtimePayload,
  DashboardRealtimeEnvelope,
  DashboardStatsUpdatePayload,
} from "../types/realtime";

export const DASHBOARD_STATS_QUERY_KEY = ["dashboard", "stats"] as const;

export type DashboardRealtimeStatsSnapshot = DashboardStatsUpdatePayload;

function normalizeCountryCode(country: string | null | undefined): string | null {
  if (country === null || country === undefined) {
    return null;
  }
  const trimmed = country.trim();
  if (trimmed.length === 0) {
    return null;
  }
  return trimmed.toUpperCase();
}

function realtimePayloadToSummary(payload: DashboardPrisonerRealtimePayload): DashboardPrisonerSummary {
  const countryCode = normalizeCountryCode(payload.country_code);
  return {
    id: payload.prisoner_id,
    source_ip: payload.source_ip,
    country_code: countryCode,
    attempt_count: payload.attempt_count,
    first_seen_at: payload.first_seen_at,
    last_seen_at: payload.last_seen_at,
    credential_count: payload.credential_count,
    command_count: payload.command_count,
    download_count: payload.download_count,
    enrichment: {
      status: payload.enrichment.status,
      last_updated_at: payload.enrichment.last_updated_at,
      country_code: normalizeCountryCode(payload.enrichment.country_code),
      asn: payload.enrichment.asn,
      reputation_severity: payload.enrichment.reputation_severity,
    },
  };
}

function comparePrisonersByRecency(a: DashboardPrisonerSummary, b: DashboardPrisonerSummary): number {
  if (a.last_seen_at !== b.last_seen_at) {
    return a.last_seen_at < b.last_seen_at ? 1 : -1;
  }
  return b.id - a.id;
}

function summariesAreEqual(a: DashboardPrisonerSummary, b: DashboardPrisonerSummary): boolean {
  return (
    a.id === b.id &&
    a.source_ip === b.source_ip &&
    a.country_code === b.country_code &&
    a.attempt_count === b.attempt_count &&
    a.first_seen_at === b.first_seen_at &&
    a.last_seen_at === b.last_seen_at &&
    a.credential_count === b.credential_count &&
    a.command_count === b.command_count &&
    a.download_count === b.download_count &&
    a.enrichment.status === b.enrichment.status &&
    a.enrichment.last_updated_at === b.enrichment.last_updated_at &&
    a.enrichment.country_code === b.enrichment.country_code &&
    a.enrichment.asn === b.enrichment.asn &&
    a.enrichment.reputation_severity === b.enrichment.reputation_severity
  );
}

function extractCountryFilterFromQueryKey(queryKey: QueryKey): string | null {
  if (!Array.isArray(queryKey) || queryKey.length < 4) {
    return null;
  }
  const maybeFilter = queryKey[3];
  if (typeof maybeFilter !== "object" || maybeFilter === null || Array.isArray(maybeFilter)) {
    return null;
  }
  const country = (maybeFilter as { country?: unknown }).country;
  return normalizeCountryCode(typeof country === "string" ? country : null);
}

function matchesCountryFilter(prisoner: DashboardPrisonerSummary, countryFilter: string | null): boolean {
  if (countryFilter === null) {
    return true;
  }
  return normalizeCountryCode(prisoner.country_code) === countryFilter;
}

export function reconcilePrisonerListWithRealtimePayload(
  current: DashboardPrisonerListResponse,
  payload: DashboardPrisonerRealtimePayload,
  countryFilter: string | null,
): DashboardPrisonerListResponse {
  const incoming = realtimePayloadToSummary(payload);
  const existingIndex = current.items.findIndex((item) => item.id === incoming.id);
  const shouldInclude = matchesCountryFilter(incoming, countryFilter);

  if (!shouldInclude) {
    if (existingIndex === -1) {
      return current;
    }
    const items = current.items.filter((item) => item.id !== incoming.id);
    return {
      ...current,
      items,
    };
  }

  if (existingIndex >= 0 && summariesAreEqual(current.items[existingIndex], incoming)) {
    return current;
  }

  const items = current.items.slice();
  if (existingIndex >= 0) {
    items[existingIndex] = incoming;
  } else {
    items.push(incoming);
  }
  items.sort(comparePrisonersByRecency);

  return {
    ...current,
    items,
  };
}

function applyPrisonerPayloadAcrossCachedLists(queryClient: QueryClient, payload: DashboardPrisonerRealtimePayload): void {
  const cachedLists = queryClient.getQueriesData<DashboardPrisonerListResponse>({
    queryKey: dashboardQueryKeys.prisoners.all,
  });

  for (const [queryKey, current] of cachedLists) {
    if (!current) {
      continue;
    }
    const countryFilter = extractCountryFilterFromQueryKey(queryKey);
    const next = reconcilePrisonerListWithRealtimePayload(current, payload, countryFilter);
    if (next !== current) {
      queryClient.setQueryData(queryKey, next);
    }
  }
}

export function applyRealtimeEnvelopeToCache(queryClient: QueryClient, envelope: DashboardRealtimeEnvelope): void {
  switch (envelope.event) {
    case "new_prisoner":
    case "prisoner_updated":
    case "prisoner_enriched":
      applyPrisonerPayloadAcrossCachedLists(queryClient, envelope.payload);
      return;
    case "snapshot_chunk":
      for (const prisoner of envelope.payload.prisoners) {
        applyPrisonerPayloadAcrossCachedLists(queryClient, prisoner);
      }
      return;
    case "stats_update":
      queryClient.setQueryData<DashboardRealtimeStatsSnapshot>(DASHBOARD_STATS_QUERY_KEY, {
        ...envelope.payload,
      });
      return;
    case "welcome":
    case "sync_start":
    case "sync_complete":
      return;
  }
}
