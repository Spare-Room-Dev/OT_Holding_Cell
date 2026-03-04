import type { DashboardPrisonerSummary } from "../types/contracts";

export type DashboardTimeWindow = "15m" | "1h" | "24h" | "all";

export interface DashboardFilterState {
  country: string | null;
  timeWindow: DashboardTimeWindow;
}

export interface DashboardFilterPipelineResult {
  visiblePrisoners: DashboardPrisonerSummary[];
  filteredOutCount: number;
}

const TIME_WINDOW_TO_MILLISECONDS: Record<Exclude<DashboardTimeWindow, "all">, number> = {
  "15m": 15 * 60_000,
  "1h": 60 * 60_000,
  "24h": 24 * 60 * 60_000,
};

function normalizeCountry(country: string | null | undefined): string | null {
  if (country === null || country === undefined) {
    return null;
  }
  const trimmed = country.trim();
  return trimmed.length > 0 ? trimmed.toUpperCase() : null;
}

function isWithinTimeWindow(lastSeenAt: string, now: Date, timeWindow: DashboardTimeWindow): boolean {
  if (timeWindow === "all") {
    return true;
  }

  const lastSeenAtEpoch = Date.parse(lastSeenAt);
  if (Number.isNaN(lastSeenAtEpoch)) {
    return false;
  }

  const cutoffEpoch = now.getTime() - TIME_WINDOW_TO_MILLISECONDS[timeWindow];
  return lastSeenAtEpoch >= cutoffEpoch;
}

export function applyDashboardFilterPipeline(
  prisoners: DashboardPrisonerSummary[],
  filters: DashboardFilterState,
  now = new Date(),
): DashboardFilterPipelineResult {
  const normalizedCountry = normalizeCountry(filters.country);

  const countryFiltered = normalizedCountry
    ? prisoners.filter((prisoner) => prisoner.country_code?.toUpperCase() === normalizedCountry)
    : prisoners;

  const visiblePrisoners = countryFiltered.filter((prisoner) =>
    isWithinTimeWindow(prisoner.last_seen_at, now, filters.timeWindow),
  );

  return {
    visiblePrisoners,
    filteredOutCount: prisoners.length - visiblePrisoners.length,
  };
}
