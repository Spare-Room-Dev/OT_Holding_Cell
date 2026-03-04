import type { DashboardFilterState, DashboardTimeWindow } from "./filter-pipeline";

export interface DashboardUiState {
  selectedPrisonerId: number | null;
  filters: DashboardFilterState;
}

const DEFAULT_FILTER_STATE: DashboardFilterState = {
  country: null,
  timeWindow: "all",
};

const DEFAULT_DASHBOARD_UI_STATE: DashboardUiState = {
  selectedPrisonerId: null,
  filters: DEFAULT_FILTER_STATE,
};

let dashboardUiState: DashboardUiState = DEFAULT_DASHBOARD_UI_STATE;
const listeners = new Set<() => void>();

function normalizeCountry(country: string | null): string | null {
  if (country === null) {
    return null;
  }
  const trimmed = country.trim();
  return trimmed.length > 0 ? trimmed.toUpperCase() : null;
}

function notifyListeners(): void {
  for (const listener of listeners) {
    listener();
  }
}

function setDashboardUiState(nextState: DashboardUiState): void {
  dashboardUiState = nextState;
  notifyListeners();
}

export function getDashboardUiState(): DashboardUiState {
  return dashboardUiState;
}

export function subscribeDashboardUiState(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function setDashboardSelectedPrisonerId(prisonerId: number | null): void {
  setDashboardUiState({
    ...dashboardUiState,
    selectedPrisonerId: prisonerId,
  });
}

export function setDashboardCountryFilter(country: string | null): void {
  setDashboardUiState({
    ...dashboardUiState,
    filters: {
      ...dashboardUiState.filters,
      country: normalizeCountry(country),
    },
  });
}

export function setDashboardTimeWindowFilter(timeWindow: DashboardTimeWindow): void {
  setDashboardUiState({
    ...dashboardUiState,
    filters: {
      ...dashboardUiState.filters,
      timeWindow,
    },
  });
}

export function resetDashboardUiState(): void {
  setDashboardUiState({
    selectedPrisonerId: DEFAULT_DASHBOARD_UI_STATE.selectedPrisonerId,
    filters: {
      ...DEFAULT_FILTER_STATE,
    },
  });
}
