import { describe, expect, it } from "vitest";
import {
  DEFAULT_OFFLINE_TIMEOUT_MS,
  createInitialConnectionState,
  transitionConnectionState,
} from "./connection-state-machine";

describe("connection-state-machine", () => {
  it("transitions from live to reconnecting on disconnect and marks data stale", () => {
    const state = transitionConnectionState(
      createInitialConnectionState(),
      { type: "disconnected", at: 1_000 },
      { offlineTimeoutMs: DEFAULT_OFFLINE_TIMEOUT_MS },
    );

    expect(state.status).toBe("reconnecting");
    expect(state.isStale).toBe(true);
    expect(state.reconnectAttempt).toBe(1);
    expect(state.reconnectStartedAt).toBe(1_000);
    expect(state.offlineDeadlineAt).toBe(1_000 + DEFAULT_OFFLINE_TIMEOUT_MS);
  });

  it("transitions reconnecting to offline when timeout elapses without sync recovery", () => {
    const reconnecting = transitionConnectionState(
      createInitialConnectionState(),
      { type: "disconnected", at: 5_000 },
      { offlineTimeoutMs: 4_000 },
    );
    const stillReconnecting = transitionConnectionState(reconnecting, { type: "timer", at: 8_999 }, { offlineTimeoutMs: 4_000 });
    const offline = transitionConnectionState(reconnecting, { type: "timer", at: 9_000 }, { offlineTimeoutMs: 4_000 });

    expect(stillReconnecting.status).toBe("reconnecting");
    expect(offline.status).toBe("offline");
    expect(offline.isStale).toBe(true);
    expect(offline.offlineDeadlineAt).toBeNull();
  });

  it("stale state remains until sync completion, then returns to live", () => {
    const reconnecting = transitionConnectionState(
      createInitialConnectionState(),
      { type: "disconnected", at: 500 },
      { offlineTimeoutMs: 2_000 },
    );
    const connectedButUnsynced = transitionConnectionState(
      reconnecting,
      { type: "connected", at: 750 },
      { offlineTimeoutMs: 2_000 },
    );
    const live = transitionConnectionState(connectedButUnsynced, { type: "sync_complete", at: 1_000 }, { offlineTimeoutMs: 2_000 });

    expect(connectedButUnsynced.status).toBe("reconnecting");
    expect(connectedButUnsynced.isStale).toBe(true);
    expect(live.status).toBe("live");
    expect(live.isStale).toBe(false);
    expect(live.offlineDeadlineAt).toBeNull();
  });

  it("manual retry from offline starts a fresh reconnect attempt and resets timeout", () => {
    const reconnecting = transitionConnectionState(
      createInitialConnectionState(),
      { type: "disconnected", at: 10_000 },
      { offlineTimeoutMs: 1_000 },
    );
    const offline = transitionConnectionState(reconnecting, { type: "timer", at: 11_000 }, { offlineTimeoutMs: 1_000 });
    const retried = transitionConnectionState(offline, { type: "manual_retry", at: 12_500 }, { offlineTimeoutMs: 1_000 });

    expect(offline.status).toBe("offline");
    expect(retried.status).toBe("reconnecting");
    expect(retried.isStale).toBe(true);
    expect(retried.reconnectAttempt).toBe(2);
    expect(retried.reconnectStartedAt).toBe(12_500);
    expect(retried.offlineDeadlineAt).toBe(13_500);
  });

  it("manual retry while reconnecting resets deadline without dropping stale marker", () => {
    const reconnecting = transitionConnectionState(
      createInitialConnectionState(),
      { type: "disconnected", at: 20_000 },
      { offlineTimeoutMs: 5_000 },
    );
    const retried = transitionConnectionState(reconnecting, { type: "manual_retry", at: 22_000 }, { offlineTimeoutMs: 5_000 });

    expect(retried.status).toBe("reconnecting");
    expect(retried.isStale).toBe(true);
    expect(retried.reconnectAttempt).toBe(2);
    expect(retried.offlineDeadlineAt).toBe(27_000);
  });
});
