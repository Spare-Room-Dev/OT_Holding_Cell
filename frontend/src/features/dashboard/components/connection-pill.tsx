import type { DashboardConnectionStatus } from "../state/connection-state-machine";
import "./dashboard-layout.css";

export interface ConnectionPillProps {
  status: DashboardConnectionStatus;
  isStale: boolean;
  reconnectAttempt: number;
  onRetry: () => void;
}

const CONNECTION_LABELS: Record<DashboardConnectionStatus, string> = {
  live: "live",
  reconnecting: "reconnecting",
  offline: "offline",
};

export function ConnectionPill({ status, isStale, reconnectAttempt, onRetry }: ConnectionPillProps) {
  const showRetryMetadata = status !== "live" || reconnectAttempt > 0;
  const canRetry = status !== "live" || isStale;

  return (
    <div className={`connection-pill connection-pill--${status}`} role="status" aria-live="polite">
      <p className="connection-pill__text">Connection {CONNECTION_LABELS[status]}</p>
      {isStale ? <p className="connection-pill__meta">Data is stale until sync recovers.</p> : null}
      {showRetryMetadata ? <p className="connection-pill__meta">Reconnect attempts: {reconnectAttempt}</p> : null}
      <button type="button" className="connection-pill__retry" onClick={onRetry} disabled={!canRetry}>
        Retry
      </button>
    </div>
  );
}
