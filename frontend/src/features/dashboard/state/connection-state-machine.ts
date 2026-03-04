export type DashboardConnectionStatus = "live" | "reconnecting" | "offline";

export interface ConnectionState {
  status: DashboardConnectionStatus;
  isStale: boolean;
  reconnectAttempt: number;
  reconnectStartedAt: number | null;
  offlineDeadlineAt: number | null;
  lastTransitionAt: number;
}

export type ConnectionStateEvent =
  | { type: "connected"; at: number }
  | { type: "disconnected"; at: number }
  | { type: "sync_complete"; at: number }
  | { type: "manual_retry"; at: number }
  | { type: "timer"; at: number };

export interface ConnectionStateTransitionOptions {
  offlineTimeoutMs?: number;
}

export const DEFAULT_OFFLINE_TIMEOUT_MS = 15_000;

function resolveOfflineTimeoutMs(options?: ConnectionStateTransitionOptions): number {
  const timeoutMs = options?.offlineTimeoutMs ?? DEFAULT_OFFLINE_TIMEOUT_MS;
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    throw new Error("offlineTimeoutMs must be a positive finite number");
  }
  return timeoutMs;
}

function toReconnecting(state: ConnectionState, at: number, offlineTimeoutMs: number): ConnectionState {
  return {
    status: "reconnecting",
    isStale: true,
    reconnectAttempt: state.reconnectAttempt + 1,
    reconnectStartedAt: at,
    offlineDeadlineAt: at + offlineTimeoutMs,
    lastTransitionAt: at,
  };
}

export function createInitialConnectionState(now = 0): ConnectionState {
  return {
    status: "live",
    isStale: false,
    reconnectAttempt: 0,
    reconnectStartedAt: null,
    offlineDeadlineAt: null,
    lastTransitionAt: now,
  };
}

export function transitionConnectionState(
  state: ConnectionState,
  event: ConnectionStateEvent,
  options?: ConnectionStateTransitionOptions,
): ConnectionState {
  const offlineTimeoutMs = resolveOfflineTimeoutMs(options);

  switch (event.type) {
    case "connected":
      if (state.status === "live") {
        return {
          ...state,
          lastTransitionAt: event.at,
        };
      }

      return {
        ...state,
        status: "reconnecting",
        isStale: true,
        reconnectStartedAt: state.reconnectStartedAt ?? event.at,
        offlineDeadlineAt: state.offlineDeadlineAt ?? event.at + offlineTimeoutMs,
        lastTransitionAt: event.at,
      };
    case "disconnected":
    case "manual_retry":
      return toReconnecting(state, event.at, offlineTimeoutMs);
    case "sync_complete":
      return {
        ...state,
        status: "live",
        isStale: false,
        reconnectStartedAt: null,
        offlineDeadlineAt: null,
        lastTransitionAt: event.at,
      };
    case "timer":
      if (state.status !== "reconnecting") {
        return state;
      }
      if (state.offlineDeadlineAt === null || event.at < state.offlineDeadlineAt) {
        return state;
      }
      return {
        ...state,
        status: "offline",
        isStale: true,
        offlineDeadlineAt: null,
        lastTransitionAt: event.at,
      };
  }
}
