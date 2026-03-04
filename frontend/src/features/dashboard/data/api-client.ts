import {
  parseDashboardPrisonerDetailResponse,
  parseDashboardPrisonerListResponse,
  type DashboardPrisonerDetailResponse,
  type DashboardPrisonerListResponse,
} from "../types/contracts";

export const DEFAULT_DASHBOARD_API_BASE_URL = "https://api.holdingcell.test";

export class DashboardApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "DashboardApiError";
    this.status = status;
  }
}

export interface DashboardApiClientOptions {
  baseUrl?: string;
  signal?: AbortSignal;
}

export interface PrisonerListRequestOptions extends DashboardApiClientOptions {
  country?: string | null;
  cursor?: string | null;
  limit?: number;
}

export interface PrisonerDetailRequestOptions extends DashboardApiClientOptions {
  prisonerId: number;
}

function normalizeBaseUrl(baseUrl: string | undefined): string {
  const raw = (baseUrl ?? DEFAULT_DASHBOARD_API_BASE_URL).trim();
  const normalized = raw.replace(/\/+$/, "");
  if (normalized.length === 0) {
    throw new Error("Dashboard API base URL cannot be empty");
  }
  return normalized;
}

function buildApiUrl(pathname: string, options?: Record<string, string>): string {
  const baseUrl = normalizeBaseUrl(options?.baseUrl);
  const url = new URL(pathname, `${baseUrl}/`);
  if (options) {
    for (const [key, value] of Object.entries(options)) {
      if (key === "baseUrl") {
        continue;
      }
      url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

async function fetchJson(url: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal });

  if (!response.ok) {
    throw new DashboardApiError(`Dashboard API request failed (${response.status})`, response.status);
  }

  return response.json() as Promise<unknown>;
}

function normalizeCountry(country: string | null | undefined): string | null {
  if (country === null || country === undefined) {
    return null;
  }
  const trimmed = country.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export async function fetchPrisonerList(options: PrisonerListRequestOptions = {}): Promise<DashboardPrisonerListResponse> {
  const queryParams: Record<string, string> = {
    baseUrl: options.baseUrl ?? DEFAULT_DASHBOARD_API_BASE_URL,
  };

  const country = normalizeCountry(options.country);
  if (country !== null) {
    queryParams.country = country;
  }
  if (options.cursor) {
    queryParams.cursor = options.cursor;
  }
  if (options.limit !== undefined) {
    queryParams.limit = String(options.limit);
  }

  const payload = await fetchJson(buildApiUrl("/api/prisoners", queryParams), options.signal);
  return parseDashboardPrisonerListResponse(payload);
}

export async function fetchPrisonerDetail(
  options: PrisonerDetailRequestOptions,
): Promise<DashboardPrisonerDetailResponse> {
  const payload = await fetchJson(
    buildApiUrl(`/api/prisoners/${options.prisonerId}`, {
      baseUrl: options.baseUrl ?? DEFAULT_DASHBOARD_API_BASE_URL,
    }),
    options.signal,
  );
  return parseDashboardPrisonerDetailResponse(payload);
}
