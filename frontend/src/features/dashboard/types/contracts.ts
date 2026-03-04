export type DashboardIsoDateTime = string;

export interface DashboardPrisonerEnrichmentSummary {
  status: string;
  last_updated_at: DashboardIsoDateTime | null;
  country_code: string | null;
  asn: string | null;
  reputation_severity: string | null;
}

export interface DashboardPrisonerSummary {
  id: number;
  source_ip: string;
  country_code: string | null;
  attempt_count: number;
  first_seen_at: DashboardIsoDateTime;
  last_seen_at: DashboardIsoDateTime;
  credential_count: number;
  command_count: number;
  download_count: number;
  enrichment: DashboardPrisonerEnrichmentSummary;
}

export interface DashboardPrisonerListResponse {
  items: DashboardPrisonerSummary[];
  next_cursor: string | null;
}

export const DASHBOARD_PRISONER_SUMMARY_REQUIRED_FIELDS = [
  "id",
  "source_ip",
  "country_code",
  "attempt_count",
  "first_seen_at",
  "last_seen_at",
  "credential_count",
  "command_count",
  "download_count",
  "enrichment",
] as const;

export const DASHBOARD_PRISONER_DETAIL_REQUIRED_FIELDS = [
  "prisoner",
  "protocol_history",
  "credentials",
  "commands",
  "downloads",
] as const;

export interface DashboardPrisonerProtocolHistoryEntry {
  protocol: string;
  attempt_count: number;
  first_seen_at: DashboardIsoDateTime;
  last_seen_at: DashboardIsoDateTime;
}

export interface DashboardPrisonerCredentialHistoryEntry {
  protocol: string;
  credential: string;
  observed_at: DashboardIsoDateTime;
}

export interface DashboardPrisonerCommandHistoryEntry {
  protocol: string;
  command: string;
  observed_at: DashboardIsoDateTime;
}

export interface DashboardPrisonerDownloadHistoryEntry {
  protocol: string;
  download_url: string;
  observed_at: DashboardIsoDateTime;
}

export interface DashboardPrisonerEnrichmentGeo {
  country_code: string | null;
  asn: string | null;
}

export interface DashboardPrisonerEnrichmentReputation {
  severity: string | null;
  confidence: number | null;
}

export interface DashboardPrisonerEnrichmentDetail {
  status: string;
  last_updated_at: DashboardIsoDateTime | null;
  provider: string | null;
  geo: DashboardPrisonerEnrichmentGeo;
  reputation: DashboardPrisonerEnrichmentReputation;
  reason_metadata: Record<string, string>;
}

export interface DashboardPrisonerDetailPrisoner extends Omit<DashboardPrisonerSummary, "enrichment"> {
  enrichment: DashboardPrisonerEnrichmentDetail;
}

export interface DashboardPrisonerDetailResponse {
  prisoner: DashboardPrisonerDetailPrisoner;
  protocol_history: DashboardPrisonerProtocolHistoryEntry[];
  credentials: DashboardPrisonerCredentialHistoryEntry[];
  commands: DashboardPrisonerCommandHistoryEntry[];
  downloads: DashboardPrisonerDownloadHistoryEntry[];
}

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

function ensureNullableString(value: unknown, path: string): string | null {
  if (value === null) {
    return null;
  }
  return ensureString(value, path);
}

function ensureNonNegativeInteger(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new TypeError(`${path} must be a non-negative integer`);
  }
  return value;
}

function ensureNullableNonNegativeInteger(value: unknown, path: string): number | null {
  if (value === null) {
    return null;
  }
  return ensureNonNegativeInteger(value, path);
}

function ensureIsoDateTime(value: unknown, path: string): DashboardIsoDateTime {
  const dateString = ensureString(value, path);
  if (Number.isNaN(Date.parse(dateString))) {
    throw new TypeError(`${path} must be an ISO datetime string`);
  }
  return dateString;
}

function ensureStringMap(value: unknown, path: string): Record<string, string> {
  const obj = ensureObject(value, path);
  const map: Record<string, string> = {};
  for (const [key, entryValue] of Object.entries(obj)) {
    if (typeof entryValue !== "string") {
      throw new TypeError(`${path}.${key} must be a string`);
    }
    map[key] = entryValue;
  }
  return map;
}

function ensureArray(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new TypeError(`${path} must be an array`);
  }
  return value;
}

export function parseDashboardPrisonerEnrichmentSummary(
  value: unknown,
  path = "enrichment",
): DashboardPrisonerEnrichmentSummary {
  const obj = ensureObject(value, path);
  return {
    status: ensureString(obj.status, `${path}.status`),
    last_updated_at: obj.last_updated_at === null ? null : ensureIsoDateTime(obj.last_updated_at, `${path}.last_updated_at`),
    country_code: ensureNullableString(obj.country_code, `${path}.country_code`),
    asn: ensureNullableString(obj.asn, `${path}.asn`),
    reputation_severity: ensureNullableString(obj.reputation_severity, `${path}.reputation_severity`),
  };
}

function parseDashboardPrisonerSummary(value: unknown, path: string): DashboardPrisonerSummary {
  const obj = ensureObject(value, path);
  return {
    id: ensureNonNegativeInteger(obj.id, `${path}.id`),
    source_ip: ensureString(obj.source_ip, `${path}.source_ip`),
    country_code: ensureNullableString(obj.country_code, `${path}.country_code`),
    attempt_count: ensureNonNegativeInteger(obj.attempt_count, `${path}.attempt_count`),
    first_seen_at: ensureIsoDateTime(obj.first_seen_at, `${path}.first_seen_at`),
    last_seen_at: ensureIsoDateTime(obj.last_seen_at, `${path}.last_seen_at`),
    credential_count: ensureNonNegativeInteger(obj.credential_count, `${path}.credential_count`),
    command_count: ensureNonNegativeInteger(obj.command_count, `${path}.command_count`),
    download_count: ensureNonNegativeInteger(obj.download_count, `${path}.download_count`),
    enrichment: parseDashboardPrisonerEnrichmentSummary(obj.enrichment, `${path}.enrichment`),
  };
}

function parseDashboardPrisonerEnrichmentGeo(value: unknown, path: string): DashboardPrisonerEnrichmentGeo {
  const obj = ensureObject(value, path);
  return {
    country_code: ensureNullableString(obj.country_code, `${path}.country_code`),
    asn: ensureNullableString(obj.asn, `${path}.asn`),
  };
}

function parseDashboardPrisonerEnrichmentReputation(
  value: unknown,
  path: string,
): DashboardPrisonerEnrichmentReputation {
  const obj = ensureObject(value, path);
  return {
    severity: ensureNullableString(obj.severity, `${path}.severity`),
    confidence: ensureNullableNonNegativeInteger(obj.confidence, `${path}.confidence`),
  };
}

function parseDashboardPrisonerEnrichmentDetail(value: unknown, path: string): DashboardPrisonerEnrichmentDetail {
  const obj = ensureObject(value, path);
  return {
    status: ensureString(obj.status, `${path}.status`),
    last_updated_at: obj.last_updated_at === null ? null : ensureIsoDateTime(obj.last_updated_at, `${path}.last_updated_at`),
    provider: ensureNullableString(obj.provider, `${path}.provider`),
    geo: parseDashboardPrisonerEnrichmentGeo(obj.geo, `${path}.geo`),
    reputation: parseDashboardPrisonerEnrichmentReputation(obj.reputation, `${path}.reputation`),
    reason_metadata: ensureStringMap(obj.reason_metadata, `${path}.reason_metadata`),
  };
}

function parseDashboardPrisonerDetailPrisoner(
  value: unknown,
  path: string,
): DashboardPrisonerDetailPrisoner {
  const summary = parseDashboardPrisonerSummary(value, path);
  const obj = ensureObject(value, path);
  return {
    ...summary,
    enrichment: parseDashboardPrisonerEnrichmentDetail(obj.enrichment, `${path}.enrichment`),
  };
}

function parseDashboardProtocolHistoryEntry(value: unknown, path: string): DashboardPrisonerProtocolHistoryEntry {
  const obj = ensureObject(value, path);
  return {
    protocol: ensureString(obj.protocol, `${path}.protocol`),
    attempt_count: ensureNonNegativeInteger(obj.attempt_count, `${path}.attempt_count`),
    first_seen_at: ensureIsoDateTime(obj.first_seen_at, `${path}.first_seen_at`),
    last_seen_at: ensureIsoDateTime(obj.last_seen_at, `${path}.last_seen_at`),
  };
}

function parseDashboardCredentialEntry(value: unknown, path: string): DashboardPrisonerCredentialHistoryEntry {
  const obj = ensureObject(value, path);
  return {
    protocol: ensureString(obj.protocol, `${path}.protocol`),
    credential: ensureString(obj.credential, `${path}.credential`),
    observed_at: ensureIsoDateTime(obj.observed_at, `${path}.observed_at`),
  };
}

function parseDashboardCommandEntry(value: unknown, path: string): DashboardPrisonerCommandHistoryEntry {
  const obj = ensureObject(value, path);
  return {
    protocol: ensureString(obj.protocol, `${path}.protocol`),
    command: ensureString(obj.command, `${path}.command`),
    observed_at: ensureIsoDateTime(obj.observed_at, `${path}.observed_at`),
  };
}

function parseDashboardDownloadEntry(value: unknown, path: string): DashboardPrisonerDownloadHistoryEntry {
  const obj = ensureObject(value, path);
  return {
    protocol: ensureString(obj.protocol, `${path}.protocol`),
    download_url: ensureString(obj.download_url, `${path}.download_url`),
    observed_at: ensureIsoDateTime(obj.observed_at, `${path}.observed_at`),
  };
}

export function parseDashboardPrisonerListResponse(value: unknown): DashboardPrisonerListResponse {
  const obj = ensureObject(value, "DashboardPrisonerListResponse");
  const items = ensureArray(obj.items, "DashboardPrisonerListResponse.items");
  return {
    items: items.map((entry, index) => parseDashboardPrisonerSummary(entry, `DashboardPrisonerListResponse.items[${index}]`)),
    next_cursor: ensureNullableString(obj.next_cursor, "DashboardPrisonerListResponse.next_cursor"),
  };
}

export function parseDashboardPrisonerDetailResponse(value: unknown): DashboardPrisonerDetailResponse {
  const obj = ensureObject(value, "DashboardPrisonerDetailResponse");
  const protocolHistory = ensureArray(obj.protocol_history, "DashboardPrisonerDetailResponse.protocol_history");
  const credentials = ensureArray(obj.credentials, "DashboardPrisonerDetailResponse.credentials");
  const commands = ensureArray(obj.commands, "DashboardPrisonerDetailResponse.commands");
  const downloads = ensureArray(obj.downloads, "DashboardPrisonerDetailResponse.downloads");

  return {
    prisoner: parseDashboardPrisonerDetailPrisoner(obj.prisoner, "DashboardPrisonerDetailResponse.prisoner"),
    protocol_history: protocolHistory.map((entry, index) =>
      parseDashboardProtocolHistoryEntry(entry, `DashboardPrisonerDetailResponse.protocol_history[${index}]`),
    ),
    credentials: credentials.map((entry, index) =>
      parseDashboardCredentialEntry(entry, `DashboardPrisonerDetailResponse.credentials[${index}]`),
    ),
    commands: commands.map((entry, index) =>
      parseDashboardCommandEntry(entry, `DashboardPrisonerDetailResponse.commands[${index}]`),
    ),
    downloads: downloads.map((entry, index) =>
      parseDashboardDownloadEntry(entry, `DashboardPrisonerDetailResponse.downloads[${index}]`),
    ),
  };
}
