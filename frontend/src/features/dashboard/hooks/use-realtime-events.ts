import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  DEFAULT_OFFLINE_TIMEOUT_MS,
  createInitialConnectionState,
  transitionConnectionState,
  type ConnectionState,
  type ConnectionStateTransitionOptions,
} from "../state/connection-state-machine";
import { applyRealtimeEnvelopeToCache } from "../state/realtime-reconcile";
import { parseDashboardRealtimeEnvelope } from "../types/realtime";

export interface RealtimeWebSocketLike {
  addEventListener(type: string, listener: (event: unknown) => void): void;
  removeEventListener(type: string, listener: (event: unknown) => void): void;
  close(): void;
}

export type RealtimeWebSocketFactory = (url: string) => RealtimeWebSocketLike;

export interface UseRealtimeEventsOptions extends ConnectionStateTransitionOptions {
  websocketUrl: string;
  websocketFactory?: RealtimeWebSocketFactory;
  reconnectDelayMs?: number;
  enabled?: boolean;
  now?: () => number;
}

export interface UseRealtimeEventsResult {
  connectionStatus: ConnectionState["status"];
  isStale: boolean;
  reconnectAttempt: number;
  retryConnection: () => void;
}

export const DEFAULT_RECONNECT_DELAY_MS = 1_000;

function parseMessageEnvelope(data: unknown) {
  const candidate = typeof data === "string" ? JSON.parse(data) : data;
  return parseDashboardRealtimeEnvelope(candidate);
}

function createBrowserWebSocket(url: string): RealtimeWebSocketLike {
  return new WebSocket(url);
}

export function useRealtimeEvents(options: UseRealtimeEventsOptions): UseRealtimeEventsResult {
  const queryClient = useQueryClient();
  const websocketFactory = options.websocketFactory ?? createBrowserWebSocket;
  const reconnectDelayMs = options.reconnectDelayMs ?? DEFAULT_RECONNECT_DELAY_MS;
  const offlineTimeoutMs = options.offlineTimeoutMs ?? DEFAULT_OFFLINE_TIMEOUT_MS;
  const enabled = options.enabled ?? true;
  const now = useCallback(() => {
    if (options.now) {
      return options.now();
    }
    return Date.now();
  }, [options.now]);

  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const offlineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const socketRef = useRef<RealtimeWebSocketLike | null>(null);
  const expectedCloseRef = useRef(false);

  const [connectionState, setConnectionState] = useState(() => createInitialConnectionState(now()));
  const [sessionNonce, setSessionNonce] = useState(0);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const applyTransition = useCallback(
    (event: Parameters<typeof transitionConnectionState>[1]) => {
      setConnectionState((previous) => {
        const next = transitionConnectionState(previous, event, { offlineTimeoutMs });

        if (offlineTimerRef.current !== null) {
          clearTimeout(offlineTimerRef.current);
          offlineTimerRef.current = null;
        }

        if (next.status === "reconnecting" && next.offlineDeadlineAt !== null) {
          const timeoutMs = Math.max(0, next.offlineDeadlineAt - now());
          offlineTimerRef.current = setTimeout(() => {
            setConnectionState((current) =>
              transitionConnectionState(current, { type: "timer", at: now() }, { offlineTimeoutMs }),
            );
            offlineTimerRef.current = null;
          }, timeoutMs);
        }

        return next;
      });
    },
    [now, offlineTimeoutMs],
  );

  const scheduleReconnect = useCallback(() => {
    if (reconnectDelayMs < 0) {
      return;
    }
    clearReconnectTimer();
    reconnectTimerRef.current = setTimeout(() => {
      setSessionNonce((current) => current + 1);
      reconnectTimerRef.current = null;
    }, reconnectDelayMs);
  }, [clearReconnectTimer, reconnectDelayMs]);

  useEffect(() => {
    if (!enabled) {
      clearReconnectTimer();
      if (offlineTimerRef.current !== null) {
        clearTimeout(offlineTimerRef.current);
        offlineTimerRef.current = null;
      }
      expectedCloseRef.current = true;
      socketRef.current?.close();
      socketRef.current = null;
      return;
    }

    expectedCloseRef.current = false;
    const socket = websocketFactory(options.websocketUrl);
    socketRef.current = socket;

    const handleOpen = () => {
      applyTransition({ type: "connected", at: now() });
    };

    const handleClose = () => {
      if (expectedCloseRef.current) {
        return;
      }
      applyTransition({ type: "disconnected", at: now() });
      scheduleReconnect();
    };

    const handleMessage = (event: unknown) => {
      try {
        const messageData =
          typeof event === "object" && event !== null && "data" in event
            ? (event as { data?: unknown }).data
            : undefined;
        const envelope = parseMessageEnvelope(messageData);
        applyRealtimeEnvelopeToCache(queryClient, envelope);
        if (envelope.event === "sync_complete") {
          applyTransition({ type: "sync_complete", at: now() });
        }
      } catch {
        // Ignore malformed events; parser already enforces schema constraints.
      }
    };

    socket.addEventListener("open", handleOpen);
    socket.addEventListener("close", handleClose);
    socket.addEventListener("message", handleMessage);

    return () => {
      expectedCloseRef.current = true;
      socket.removeEventListener("open", handleOpen);
      socket.removeEventListener("close", handleClose);
      socket.removeEventListener("message", handleMessage);
      socket.close();
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [
    applyTransition,
    clearReconnectTimer,
    enabled,
    now,
    options.websocketUrl,
    queryClient,
    scheduleReconnect,
    sessionNonce,
    websocketFactory,
  ]);

  useEffect(() => {
    return () => {
      clearReconnectTimer();
      if (offlineTimerRef.current !== null) {
        clearTimeout(offlineTimerRef.current);
        offlineTimerRef.current = null;
      }
      expectedCloseRef.current = true;
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [clearReconnectTimer]);

  const retryConnection = useCallback(() => {
    if (!enabled) {
      return;
    }
    clearReconnectTimer();
    applyTransition({ type: "manual_retry", at: now() });
    setSessionNonce((current) => current + 1);
  }, [applyTransition, clearReconnectTimer, enabled, now]);

  return {
    connectionStatus: connectionState.status,
    isStale: connectionState.isStale,
    reconnectAttempt: connectionState.reconnectAttempt,
    retryConnection,
  };
}
