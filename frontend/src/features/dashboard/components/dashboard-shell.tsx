import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useDashboardFilters } from "../hooks/use-dashboard-filters";
import { usePrisonerDetail } from "../hooks/use-prisoner-detail";
import { usePrisonerList } from "../hooks/use-prisoner-list";
import { useRealtimeEvents, type RealtimeWebSocketFactory } from "../hooks/use-realtime-events";
import { DASHBOARD_STATS_QUERY_KEY, type DashboardRealtimeStatsSnapshot } from "../state/realtime-reconcile";
import { DetailPane } from "./detail-pane";
import { FilterBar } from "./filter-bar";
import { MobileDetailDrawer } from "./mobile-detail-drawer";
import { PrisonerList } from "./prisoner-list";
import { StatsBar, type DashboardStatsSnapshot } from "./stats-bar";
import { ConnectionPill } from "./connection-pill";
import "./dashboard-layout.css";

const MOBILE_LAYOUT_MEDIA_QUERY = "(max-width: 64rem)";

export interface DashboardShellProps {
  apiBaseUrl?: string;
  websocketUrl: string;
  websocketFactory?: RealtimeWebSocketFactory;
  realtimeEnabled?: boolean;
  forceMobileLayout?: boolean;
  now?: () => number;
}

function deriveCountryOptions(candidates: Array<string | null>): string[] {
  const uniqueCountryCodes = new Set<string>();
  for (const countryCode of candidates) {
    if (countryCode === null) {
      continue;
    }
    const trimmed = countryCode.trim().toUpperCase();
    if (trimmed.length === 0) {
      continue;
    }
    uniqueCountryCodes.add(trimmed);
  }
  return [...uniqueCountryCodes].sort((a, b) => a.localeCompare(b, "en-US"));
}

function deriveFallbackStats(attemptCounts: number[], credentialCounts: number[], commandCounts: number[], downloadCounts: number[]) {
  const sum = (values: number[]) => values.reduce((total, value) => total + value, 0);
  return {
    totalPrisoners: attemptCounts.length,
    activePrisoners: attemptCounts.length,
    lifetimeAttempts: sum(attemptCounts),
    lifetimeCredentials: sum(credentialCounts),
    lifetimeCommands: sum(commandCounts),
    lifetimeDownloads: sum(downloadCounts),
  };
}

function mapRealtimeStatsSnapshot(snapshot: DashboardRealtimeStatsSnapshot): DashboardStatsSnapshot {
  return {
    totalPrisoners: snapshot.total_prisoners,
    activePrisoners: snapshot.active_prisoners,
    lifetimeAttempts: snapshot.lifetime_attempts,
    lifetimeCredentials: snapshot.lifetime_credentials,
    lifetimeCommands: snapshot.lifetime_commands,
    lifetimeDownloads: snapshot.lifetime_downloads,
  };
}

function useMobileLayout(forceMobileLayout?: boolean): boolean {
  const [isMobileLayout, setIsMobileLayout] = useState(() => forceMobileLayout ?? false);

  useEffect(() => {
    if (forceMobileLayout !== undefined) {
      setIsMobileLayout(forceMobileLayout);
      return;
    }

    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      setIsMobileLayout(false);
      return;
    }

    const mediaQuery = window.matchMedia(MOBILE_LAYOUT_MEDIA_QUERY);
    const updateLayout = () => {
      setIsMobileLayout(mediaQuery.matches);
    };

    updateLayout();
    mediaQuery.addEventListener("change", updateLayout);
    return () => {
      mediaQuery.removeEventListener("change", updateLayout);
    };
  }, [forceMobileLayout]);

  return isMobileLayout;
}

export function DashboardShell({
  apiBaseUrl,
  websocketUrl,
  websocketFactory,
  realtimeEnabled = true,
  forceMobileLayout,
  now,
}: DashboardShellProps) {
  const listQuery = usePrisonerList({
    baseUrl: apiBaseUrl,
    enabled: true,
  });

  const allPrisoners = listQuery.data?.items ?? [];
  const {
    selectedPrisonerId,
    filters,
    visiblePrisoners,
    filteredOutCount,
    setSelectedPrisonerId,
    setCountryFilter,
    setTimeWindowFilter,
  } = useDashboardFilters(allPrisoners);

  const detailQuery = usePrisonerDetail({
    baseUrl: apiBaseUrl,
    prisonerId: selectedPrisonerId,
  });

  const realtime = useRealtimeEvents({
    websocketUrl,
    websocketFactory,
    enabled: realtimeEnabled,
    now,
  });

  const statsSnapshotQuery = useQuery<DashboardRealtimeStatsSnapshot | null>({
    queryKey: DASHBOARD_STATS_QUERY_KEY,
    queryFn: async () => null,
    enabled: false,
    initialData: null,
  });

  const stats = useMemo(() => {
    if (statsSnapshotQuery.data !== null) {
      return mapRealtimeStatsSnapshot(statsSnapshotQuery.data);
    }
    return deriveFallbackStats(
      allPrisoners.map((prisoner) => prisoner.attempt_count),
      allPrisoners.map((prisoner) => prisoner.credential_count),
      allPrisoners.map((prisoner) => prisoner.command_count),
      allPrisoners.map((prisoner) => prisoner.download_count),
    );
  }, [allPrisoners, statsSnapshotQuery.data]);

  const countryOptions = useMemo(
    () =>
      deriveCountryOptions(
        allPrisoners.flatMap((prisoner) => [prisoner.country_code, prisoner.enrichment.country_code]),
      ),
    [allPrisoners],
  );

  const isMobileLayout = useMobileLayout(forceMobileLayout);
  const detailPane = (
    <DetailPane
      selectedPrisonerId={selectedPrisonerId}
      detail={selectedPrisonerId === null ? null : (detailQuery.data ?? null)}
    />
  );

  return (
    <div className="dashboard-layout">
      <header className="dashboard-panel dashboard-shell__header">
        <div>
          <h1 className="dashboard-shell__title">Holding Cell Analyst Dashboard</h1>
          <p className="dashboard-shell__subtitle">
            Monitor attacker activity with live state, filtering, and explicit analyst-driven detail inspection.
          </p>
          {realtime.isStale ? (
            <p className="dashboard-shell__stale" role="status" aria-live="polite">
              Live feed is stale while the connection is recovering. Last-known prisoner data remains visible.
            </p>
          ) : null}
        </div>
        <ConnectionPill
          status={realtime.connectionStatus}
          isStale={realtime.isStale}
          reconnectAttempt={realtime.reconnectAttempt}
          onRetry={realtime.retryConnection}
        />
      </header>

      <StatsBar stats={stats} />

      <FilterBar
        country={filters.country}
        timeWindow={filters.timeWindow}
        countryOptions={countryOptions}
        filteredOutCount={filteredOutCount}
        onCountryChange={setCountryFilter}
        onTimeWindowChange={setTimeWindowFilter}
      />

      {listQuery.isError ? (
        <section className="dashboard-panel" role="alert">
          <h2 className="dashboard-panel__title">Prisoner feed unavailable</h2>
          <p className="dashboard-panel__subtitle">{listQuery.error?.message ?? "Unable to load prisoner list."}</p>
        </section>
      ) : null}

      <section className="dashboard-layout__content">
        <PrisonerList
          prisoners={visiblePrisoners}
          selectedPrisonerId={selectedPrisonerId}
          onSelectPrisoner={setSelectedPrisonerId}
          filteredOutCount={filteredOutCount}
        />
        {isMobileLayout ? null : detailPane}
      </section>

      {isMobileLayout ? (
        <MobileDetailDrawer
          isOpen={selectedPrisonerId !== null}
          onClose={() => setSelectedPrisonerId(null)}
        >
          {detailPane}
        </MobileDetailDrawer>
      ) : null}
    </div>
  );
}
