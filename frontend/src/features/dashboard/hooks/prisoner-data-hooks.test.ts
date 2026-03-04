import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchPrisonerDetail, fetchPrisonerList } from "../data/api-client";
import { dashboardQueryKeys } from "../data/query-keys";
import { createPrisonerDetailQueryOptions } from "./use-prisoner-detail";
import { createPrisonerListQueryOptions } from "./use-prisoner-list";

const listResponse = {
  items: [
    {
      id: 11,
      source_ip: "198.51.100.10",
      country_code: "US",
      attempt_count: 4,
      first_seen_at: "2026-03-04T00:00:00Z",
      last_seen_at: "2026-03-04T00:10:00Z",
      credential_count: 1,
      command_count: 2,
      download_count: 0,
      enrichment: {
        status: "pending",
        last_updated_at: null,
        country_code: "US",
        asn: null,
        reputation_severity: null,
      },
    },
  ],
  next_cursor: null,
};

const detailResponse = {
  prisoner: {
    id: 11,
    source_ip: "198.51.100.10",
    country_code: "US",
    attempt_count: 4,
    first_seen_at: "2026-03-04T00:00:00Z",
    last_seen_at: "2026-03-04T00:10:00Z",
    credential_count: 1,
    command_count: 2,
    download_count: 0,
    enrichment: {
      status: "pending",
      last_updated_at: null,
      provider: null,
      geo: {
        country_code: "US",
        asn: null,
      },
      reputation: {
        severity: null,
        confidence: null,
      },
      reason_metadata: {},
    },
  },
  protocol_history: [],
  credentials: [],
  commands: [],
  downloads: [],
};

describe("dashboard prisoner data hooks", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("builds deterministic query keys for list/detail data", () => {
    expect(dashboardQueryKeys.prisoners.list({ country: null })).toEqual([
      "dashboard",
      "prisoners",
      "list",
      { country: null },
    ]);
    expect(dashboardQueryKeys.prisoners.list({ country: "US" })).toEqual([
      "dashboard",
      "prisoners",
      "list",
      { country: "US" },
    ]);
    expect(dashboardQueryKeys.prisoners.detail(11)).toEqual([
      "dashboard",
      "prisoners",
      "detail",
      11,
    ]);
  });

  it("sends country filters to the prisoner list endpoint", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(listResponse), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    const response = await fetchPrisonerList({
      baseUrl: "https://api.holdingcell.test",
      country: "US",
    });

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith("https://api.holdingcell.test/api/prisoners?country=US", {
      signal: undefined,
    });
    expect(response.items).toHaveLength(1);
  });

  it("keeps prisoner detail queries disabled until a prisoner is selected", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(detailResponse), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    const idleDetailOptions = createPrisonerDetailQueryOptions({
      prisonerId: null,
      baseUrl: "https://api.holdingcell.test",
    });
    expect(idleDetailOptions.enabled).toBe(false);

    const activeDetailOptions = createPrisonerDetailQueryOptions({
      prisonerId: 11,
      baseUrl: "https://api.holdingcell.test",
    });

    expect(activeDetailOptions.enabled).toBe(true);
    expect(activeDetailOptions.queryKey).toEqual(["dashboard", "prisoners", "detail", 11]);

    const detail = await fetchPrisonerDetail({
      baseUrl: "https://api.holdingcell.test",
      prisonerId: 11,
    });

    expect(fetch).toHaveBeenCalledWith("https://api.holdingcell.test/api/prisoners/11", {
      signal: undefined,
    });
    expect(detail.prisoner.id).toBe(11);
  });

  it("builds list query options with country-aware cache keys", () => {
    const listOptions = createPrisonerListQueryOptions({
      baseUrl: "https://api.holdingcell.test",
      country: "US",
    });

    expect(listOptions.queryKey).toEqual(["dashboard", "prisoners", "list", { country: "US" }]);
  });
});
