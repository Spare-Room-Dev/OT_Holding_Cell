import "./dashboard-layout.css";

export interface DashboardStatsSnapshot {
  totalPrisoners: number;
  activePrisoners: number;
  lifetimeAttempts: number;
  lifetimeCredentials: number;
  lifetimeCommands: number;
  lifetimeDownloads: number;
}

export interface StatsBarProps {
  stats: DashboardStatsSnapshot;
}

function formatStat(value: number): string {
  return value.toLocaleString("en-US");
}

export function StatsBar({ stats }: StatsBarProps) {
  return (
    <section
      className="dashboard-panel dashboard-shell__metrics-band"
      aria-label="Dashboard stats"
      data-command-center-region="kpi-band"
    >
      <div className="stats-bar stats-bar--command-band">
        <article className="stats-bar__item stats-bar__item--command">
          <p className="stats-bar__label command-band__label">Total prisoners</p>
          <p className="stats-bar__value command-band__readout">{formatStat(stats.totalPrisoners)}</p>
        </article>

        <article className="stats-bar__item stats-bar__item--command">
          <p className="stats-bar__label command-band__label">Active prisoners</p>
          <p className="stats-bar__value command-band__readout">{formatStat(stats.activePrisoners)}</p>
        </article>

        <article className="stats-bar__item stats-bar__item--command">
          <p className="stats-bar__label command-band__label">Lifetime attempts</p>
          <p className="stats-bar__value command-band__readout">{formatStat(stats.lifetimeAttempts)}</p>
        </article>

        <article className="stats-bar__item stats-bar__item--command">
          <p className="stats-bar__label command-band__label">Lifetime credentials</p>
          <p className="stats-bar__value command-band__readout">{formatStat(stats.lifetimeCredentials)}</p>
        </article>

        <article className="stats-bar__item stats-bar__item--command">
          <p className="stats-bar__label command-band__label">Lifetime commands</p>
          <p className="stats-bar__value command-band__readout">{formatStat(stats.lifetimeCommands)}</p>
        </article>

        <article className="stats-bar__item stats-bar__item--command">
          <p className="stats-bar__label command-band__label">Lifetime downloads</p>
          <p className="stats-bar__value command-band__readout">{formatStat(stats.lifetimeDownloads)}</p>
        </article>
      </div>
    </section>
  );
}
