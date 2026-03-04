import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchPrisonerDetail, type DashboardApiClientOptions } from "../data/api-client";
import { dashboardQueryKeys } from "../data/query-keys";
import type { DashboardPrisonerDetailResponse } from "../types/contracts";

export interface UsePrisonerDetailOptions extends DashboardApiClientOptions {
  prisonerId: number | null;
  enabled?: boolean;
}

export function createPrisonerDetailQueryOptions(options: UsePrisonerDetailOptions) {
  const isSelected = options.prisonerId !== null;

  return {
    queryKey: dashboardQueryKeys.prisoners.detail(options.prisonerId),
    queryFn: ({ signal }: { signal?: AbortSignal }) => {
      if (options.prisonerId === null) {
        throw new Error("Cannot fetch prisoner detail without an explicit prisoner selection");
      }
      return fetchPrisonerDetail({
        baseUrl: options.baseUrl,
        prisonerId: options.prisonerId,
        signal,
      });
    },
    enabled: (options.enabled ?? true) && isSelected,
  };
}

export function usePrisonerDetail(
  options: UsePrisonerDetailOptions,
): UseQueryResult<DashboardPrisonerDetailResponse, Error> {
  return useQuery(createPrisonerDetailQueryOptions(options));
}
