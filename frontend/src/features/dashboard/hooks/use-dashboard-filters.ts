import { useMemo, useSyncExternalStore } from "react";
import type { DashboardPrisonerSummary } from "../types/contracts";
import {
  getDashboardUiState,
  setDashboardCountryFilter,
  setDashboardSelectedPrisonerId,
  setDashboardTimeWindowFilter,
  subscribeDashboardUiState,
} from "../state/dashboard-ui-store";
import { applyDashboardFilterPipeline, type DashboardFilterState } from "../state/filter-pipeline";

export function deriveDashboardFiltersResult(
  prisoners: DashboardPrisonerSummary[],
  filters: DashboardFilterState,
  now = new Date(),
) {
  return applyDashboardFilterPipeline(prisoners, filters, now);
}

export function useDashboardFilters(prisoners: DashboardPrisonerSummary[], now?: Date) {
  const uiState = useSyncExternalStore(subscribeDashboardUiState, getDashboardUiState, getDashboardUiState);
  const effectiveNow = now ?? new Date();

  const filterResult = useMemo(
    () => deriveDashboardFiltersResult(prisoners, uiState.filters, effectiveNow),
    [prisoners, uiState.filters, effectiveNow],
  );

  return {
    selectedPrisonerId: uiState.selectedPrisonerId,
    filters: uiState.filters,
    visiblePrisoners: filterResult.visiblePrisoners,
    filteredOutCount: filterResult.filteredOutCount,
    setSelectedPrisonerId: setDashboardSelectedPrisonerId,
    setCountryFilter: setDashboardCountryFilter,
    setTimeWindowFilter: setDashboardTimeWindowFilter,
  };
}
