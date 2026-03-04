import {
  type DashboardIsoDateTime,
  type DashboardPrisonerEnrichmentSummary,
  parseDashboardPrisonerEnrichmentSummary,
} from "./contracts";

export const DASHBOARD_REALTIME_EVENT_NAMES = [
  "welcome",
  "sync_start",
  "snapshot_chunk",
  "sync_complete",
  "new_prisoner",
  "prisoner_updated",
  "prisoner_enriched",
  "stats_update",
] as const;

export type RealtimeEventName = (typeof DASHBOARD_REALTIME_EVENT_NAMES)[number];

export interface DashboardRealtimeOrdering {
  publish_sequence: number;
  source_updated_at: DashboardIsoDateTime;
}

export interface DashboardWelcomePayload {
  ordering: DashboardRealtimeOrdering;
  server_time: DashboardIsoDateTime;
}

export interface DashboardSyncLifecyclePayload {
  ordering: DashboardRealtimeOrdering;
  sync_id: string;
  estimated_total_chunks: number;
}

export interface DashboardPrisonerRealtimePayload {
  ordering: DashboardRealtimeOrdering;
  prisoner_id: number;
  source_ip: string;
  country_code: string | null;
  attempt_count: number;
  first_seen_at: DashboardIsoDateTime;
  last_seen_at: DashboardIsoDateTime;
  credential_count: number;
  command_count: number;
  download_count: number;
  enrichment: DashboardPrisonerEnrichmentSummary;
  detail_sync_stale: boolean;
  detail_last_changed_at: DashboardIsoDateTime;
}

export interface DashboardSnapshotChunkPayload {
  ordering: DashboardRealtimeOrdering;
  sync_id: string;
  chunk_index: number;
  total_chunks: number;
  prisoners: DashboardPrisonerRealtimePayload[];
}

export interface DashboardStatsUpdatePayload {
  ordering: DashboardRealtimeOrdering;
  total_prisoners: number;
  active_prisoners: number;
  lifetime_attempts: number;
  lifetime_credentials: number;
  lifetime_commands: number;
  lifetime_downloads: number;
  changed: boolean;
}

export interface DashboardRealtimePayloadByEvent {
  welcome: DashboardWelcomePayload;
  sync_start: DashboardSyncLifecyclePayload;
  snapshot_chunk: DashboardSnapshotChunkPayload;
  sync_complete: DashboardSyncLifecyclePayload;
  new_prisoner: DashboardPrisonerRealtimePayload;
  prisoner_updated: DashboardPrisonerRealtimePayload;
  prisoner_enriched: DashboardPrisonerRealtimePayload;
  stats_update: DashboardStatsUpdatePayload;
}

export type DashboardRealtimeEnvelope<E extends RealtimeEventName = RealtimeEventName> = {
  event_id: string;
  event: E;
  occurred_at: DashboardIsoDateTime;
  protocol_version: string;
  payload: DashboardRealtimePayloadByEvent[E];
};

type JsonObject = Record<string, unknown>;

function ensureObject(value: unknown, path: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new TypeError(`${path} must be an object`);
  }
  return value as JsonObject;
}

function ensureString(value: unknown, path: string): string {
  if (typeof value !== "string") {
    throw new TypeError(`${path} must be a string`);
  }
  return value;
}

function ensureIsoDateTime(value: unknown, path: string): DashboardIsoDateTime {
  const dateString = ensureString(value, path);
  if (Number.isNaN(Date.parse(dateString))) {
    throw new TypeError(`${path} must be an ISO datetime string`);
  }
  return dateString;
}

function ensureNonNegativeInteger(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new TypeError(`${path} must be a non-negative integer`);
  }
  return value;
}

function ensureNullableString(value: unknown, path: string): string | null {
  if (value === null) {
    return null;
  }
  return ensureString(value, path);
}

function ensureBoolean(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") {
    throw new TypeError(`${path} must be a boolean`);
  }
  return value;
}

function ensureArray(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new TypeError(`${path} must be an array`);
  }
  return value;
}

function parseOrdering(value: unknown, path: string): DashboardRealtimeOrdering {
  const obj = ensureObject(value, path);
  return {
    publish_sequence: ensureNonNegativeInteger(obj.publish_sequence, `${path}.publish_sequence`),
    source_updated_at: ensureIsoDateTime(obj.source_updated_at, `${path}.source_updated_at`),
  };
}

function parseWelcomePayload(value: unknown, path: string): DashboardWelcomePayload {
  const obj = ensureObject(value, path);
  return {
    ordering: parseOrdering(obj.ordering, `${path}.ordering`),
    server_time: ensureIsoDateTime(obj.server_time, `${path}.server_time`),
  };
}

function parseSyncLifecyclePayload(value: unknown, path: string): DashboardSyncLifecyclePayload {
  const obj = ensureObject(value, path);
  return {
    ordering: parseOrdering(obj.ordering, `${path}.ordering`),
    sync_id: ensureString(obj.sync_id, `${path}.sync_id`),
    estimated_total_chunks: ensureNonNegativeInteger(obj.estimated_total_chunks, `${path}.estimated_total_chunks`),
  };
}

function parsePrisonerPayload(value: unknown, path: string): DashboardPrisonerRealtimePayload {
  const obj = ensureObject(value, path);
  return {
    ordering: parseOrdering(obj.ordering, `${path}.ordering`),
    prisoner_id: ensureNonNegativeInteger(obj.prisoner_id, `${path}.prisoner_id`),
    source_ip: ensureString(obj.source_ip, `${path}.source_ip`),
    country_code: ensureNullableString(obj.country_code, `${path}.country_code`),
    attempt_count: ensureNonNegativeInteger(obj.attempt_count, `${path}.attempt_count`),
    first_seen_at: ensureIsoDateTime(obj.first_seen_at, `${path}.first_seen_at`),
    last_seen_at: ensureIsoDateTime(obj.last_seen_at, `${path}.last_seen_at`),
    credential_count: ensureNonNegativeInteger(obj.credential_count, `${path}.credential_count`),
    command_count: ensureNonNegativeInteger(obj.command_count, `${path}.command_count`),
    download_count: ensureNonNegativeInteger(obj.download_count, `${path}.download_count`),
    enrichment: parseDashboardPrisonerEnrichmentSummary(obj.enrichment, `${path}.enrichment`),
    detail_sync_stale: ensureBoolean(obj.detail_sync_stale, `${path}.detail_sync_stale`),
    detail_last_changed_at: ensureIsoDateTime(obj.detail_last_changed_at, `${path}.detail_last_changed_at`),
  };
}

function parseSnapshotChunkPayload(value: unknown, path: string): DashboardSnapshotChunkPayload {
  const obj = ensureObject(value, path);
  const prisoners = ensureArray(obj.prisoners, `${path}.prisoners`);
  return {
    ordering: parseOrdering(obj.ordering, `${path}.ordering`),
    sync_id: ensureString(obj.sync_id, `${path}.sync_id`),
    chunk_index: ensureNonNegativeInteger(obj.chunk_index, `${path}.chunk_index`),
    total_chunks: ensureNonNegativeInteger(obj.total_chunks, `${path}.total_chunks`),
    prisoners: prisoners.map((entry, index) => parsePrisonerPayload(entry, `${path}.prisoners[${index}]`)),
  };
}

function parseStatsUpdatePayload(value: unknown, path: string): DashboardStatsUpdatePayload {
  const obj = ensureObject(value, path);
  return {
    ordering: parseOrdering(obj.ordering, `${path}.ordering`),
    total_prisoners: ensureNonNegativeInteger(obj.total_prisoners, `${path}.total_prisoners`),
    active_prisoners: ensureNonNegativeInteger(obj.active_prisoners, `${path}.active_prisoners`),
    lifetime_attempts: ensureNonNegativeInteger(obj.lifetime_attempts, `${path}.lifetime_attempts`),
    lifetime_credentials: ensureNonNegativeInteger(obj.lifetime_credentials, `${path}.lifetime_credentials`),
    lifetime_commands: ensureNonNegativeInteger(obj.lifetime_commands, `${path}.lifetime_commands`),
    lifetime_downloads: ensureNonNegativeInteger(obj.lifetime_downloads, `${path}.lifetime_downloads`),
    changed: ensureBoolean(obj.changed, `${path}.changed`),
  };
}

export function isRealtimeEventName(value: string): value is RealtimeEventName {
  return DASHBOARD_REALTIME_EVENT_NAMES.includes(value as RealtimeEventName);
}

export function parseDashboardRealtimeEnvelope(value: unknown): DashboardRealtimeEnvelope {
  const obj = ensureObject(value, "DashboardRealtimeEnvelope");
  const event = ensureString(obj.event, "DashboardRealtimeEnvelope.event");
  if (!isRealtimeEventName(event)) {
    throw new TypeError(`DashboardRealtimeEnvelope.event must be one of: ${DASHBOARD_REALTIME_EVENT_NAMES.join(", ")}`);
  }

  const baseEnvelope = {
    event_id: ensureString(obj.event_id, "DashboardRealtimeEnvelope.event_id"),
    event,
    occurred_at: ensureIsoDateTime(obj.occurred_at, "DashboardRealtimeEnvelope.occurred_at"),
    protocol_version: ensureString(obj.protocol_version, "DashboardRealtimeEnvelope.protocol_version"),
  };

  const payloadPath = "DashboardRealtimeEnvelope.payload";
  switch (event) {
    case "welcome":
      return { ...baseEnvelope, payload: parseWelcomePayload(obj.payload, payloadPath) };
    case "sync_start":
    case "sync_complete":
      return { ...baseEnvelope, payload: parseSyncLifecyclePayload(obj.payload, payloadPath) };
    case "snapshot_chunk":
      return { ...baseEnvelope, payload: parseSnapshotChunkPayload(obj.payload, payloadPath) };
    case "new_prisoner":
    case "prisoner_updated":
    case "prisoner_enriched":
      return { ...baseEnvelope, payload: parsePrisonerPayload(obj.payload, payloadPath) };
    case "stats_update":
      return { ...baseEnvelope, payload: parseStatsUpdatePayload(obj.payload, payloadPath) };
  }
}
