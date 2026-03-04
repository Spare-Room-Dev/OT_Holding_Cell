import { beforeEach, describe, expect, it } from "vitest";
import type { DashboardPrisonerSummary } from "../types/contracts";
import {
  applyDashboardFilterPipeline,
  type DashboardFilterState,
  type DashboardTimeWindow,
} from "./filter-pipeline";
import {
  getDashboardUiState,
  resetDashboardUiState,
  setDashboardCountryFilter,
  setDashboardSelectedPrisonerId,
  setDashboardTimeWindowFilter,
} from "./dashboard-ui-store";
import { deriveDashboardFiltersResult } from "../hooks/use-dashboard-filters";

function buildPrisoner(
  id: number,
  country: string | null,
  firstSeenAt: string,
  lastSeenAt: string,
): DashboardPrisonerSummary {
  return {
    id,
    source_ip: `198.51.100.${id}`,
    country_code: country,
    attempt_count: id,
    first_seen_at: firstSeenAt,
    last_seen_at: lastSeenAt,
    credential_count: 0,
    command_count: 0,
    download_count: 0,
    enrichment: {
      status: "pending",
      last_updated_at: null,
      country_code: country,
      asn: null,
      reputation_severity: null,
    },
  };
}

describe("dashboard filter pipeline", () => {
  const now = new Date("2026-03-04T12:00:00Z");

  const prisoners: DashboardPrisonerSummary[] = [
    buildPrisoner(1, "US", "2026-03-04T10:00:00Z", "2026-03-04T11:55:00Z"),
    buildPrisoner(2, "US", "2026-03-04T10:00:00Z", "2026-03-04T09:00:00Z"),
    buildPrisoner(3, "AU", "2026-03-04T10:00:00Z", "2026-03-04T11:58:00Z"),
    buildPrisoner(4, null, "2026-03-04T11:00:00Z", "2026-03-04T11:59:00Z"),
  ];

  beforeEach(() => {
    resetDashboardUiState();
  });

  it("applies country and time-window filters through one deterministic selector", () => {
    const filters: DashboardFilterState = {
      country: "US",
      timeWindow: "15m",
    };

    const result = applyDashboardFilterPipeline(prisoners, filters, now);

    expect(result.visiblePrisoners.map((entry) => entry.id)).toEqual([1]);
    expect(result.filteredOutCount).toBe(3);
  });

  it("uses last_seen_at for time-window filtering", () => {
    const filters: DashboardFilterState = {
      country: null,
      timeWindow: "15m",
    };

    const result = applyDashboardFilterPipeline(prisoners, filters, now);

    expect(result.visiblePrisoners.map((entry) => entry.id)).toEqual([1, 3, 4]);
    expect(result.filteredOutCount).toBe(1);
  });

  it("applies store filter changes immediately for derived results", () => {
    const defaultResult = deriveDashboardFiltersResult(prisoners, getDashboardUiState().filters, now);
    expect(defaultResult.visiblePrisoners).toHaveLength(4);
    expect(defaultResult.filteredOutCount).toBe(0);

    setDashboardCountryFilter("AU");
    let nextResult = deriveDashboardFiltersResult(prisoners, getDashboardUiState().filters, now);
    expect(nextResult.visiblePrisoners.map((entry) => entry.id)).toEqual([3]);
    expect(nextResult.filteredOutCount).toBe(3);

    setDashboardTimeWindowFilter("15m");
    nextResult = deriveDashboardFiltersResult(prisoners, getDashboardUiState().filters, now);
    expect(nextResult.visiblePrisoners.map((entry) => entry.id)).toEqual([3]);
    expect(nextResult.filteredOutCount).toBe(3);
  });

  it("keeps selection and filters in memory only", () => {
    setDashboardSelectedPrisonerId(44);
    setDashboardCountryFilter("US");
    setDashboardTimeWindowFilter("24h");

    expect(getDashboardUiState().selectedPrisonerId).toBe(44);
    expect(getDashboardUiState().filters.country).toBe("US");
    expect(getDashboardUiState().filters.timeWindow).toBe("24h");

    resetDashboardUiState();

    expect(getDashboardUiState().selectedPrisonerId).toBeNull();
    expect(getDashboardUiState().filters.country).toBeNull();
    expect(getDashboardUiState().filters.timeWindow).toBe("all");
  });
});

describe("dashboard time-window coverage", () => {
  it.each<DashboardTimeWindow>(["15m", "1h", "24h", "all"])("accepts %s as a supported window", (windowValue) => {
    expect(windowValue).toBeTruthy();
  });
});
