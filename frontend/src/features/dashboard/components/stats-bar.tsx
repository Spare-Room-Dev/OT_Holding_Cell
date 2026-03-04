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
    <section className="dashboard-panel" aria-label="Dashboard stats">
      <div className="stats-bar">
        <article className="stats-bar__item">
          <p className="stats-bar__label">Total prisoners</p>
          <p className="stats-bar__value">{formatStat(stats.totalPrisoners)}</p>
        </article>

        <article className="stats-bar__item">
          <p className="stats-bar__label">Active prisoners</p>
          <p className="stats-bar__value">{formatStat(stats.activePrisoners)}</p>
        </article>

        <article className="stats-bar__item">
          <p className="stats-bar__label">Lifetime attempts</p>
          <p className="stats-bar__value">{formatStat(stats.lifetimeAttempts)}</p>
        </article>

        <article className="stats-bar__item">
          <p className="stats-bar__label">Lifetime credentials</p>
          <p className="stats-bar__value">{formatStat(stats.lifetimeCredentials)}</p>
        </article>

        <article className="stats-bar__item">
          <p className="stats-bar__label">Lifetime commands</p>
          <p className="stats-bar__value">{formatStat(stats.lifetimeCommands)}</p>
        </article>

        <article className="stats-bar__item">
          <p className="stats-bar__label">Lifetime downloads</p>
          <p className="stats-bar__value">{formatStat(stats.lifetimeDownloads)}</p>
        </article>
      </div>
    </section>
  );
}
