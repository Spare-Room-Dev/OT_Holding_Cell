import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import {
  fetchPrisonerList,
  type DashboardApiClientOptions,
} from "../data/api-client";
import { dashboardQueryKeys } from "../data/query-keys";
import type { DashboardPrisonerListResponse } from "../types/contracts";

export interface UsePrisonerListOptions extends DashboardApiClientOptions {
  country?: string | null;
  cursor?: string | null;
  limit?: number;
  enabled?: boolean;
}

function normalizeCountry(country: string | null | undefined): string | null {
  if (country === null || country === undefined) {
    return null;
  }
  const trimmed = country.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function createPrisonerListQueryOptions(options: UsePrisonerListOptions) {
  const country = normalizeCountry(options.country);

  return {
    queryKey: dashboardQueryKeys.prisoners.list({ country }),
    queryFn: ({ signal }: { signal?: AbortSignal }) =>
      fetchPrisonerList({
        baseUrl: options.baseUrl,
        country,
        cursor: options.cursor,
        limit: options.limit,
        signal,
      }),
    enabled: options.enabled ?? true,
  };
}

export function usePrisonerList(options: UsePrisonerListOptions = {}): UseQueryResult<DashboardPrisonerListResponse, Error> {
  return useQuery(createPrisonerListQueryOptions(options));
}
