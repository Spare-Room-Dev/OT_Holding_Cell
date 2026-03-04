import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  parseDashboardPrisonerDetailResponse,
  parseDashboardPrisonerListResponse,
} from "./contracts";
import { DASHBOARD_REALTIME_EVENT_NAMES } from "./realtime";

const projectRoot = process.cwd();

function sourceAt(pathFromRoot: string): string {
  return readFileSync(resolve(projectRoot, pathFromRoot), "utf8");
}

describe("dashboard contract foundation", () => {
  it("includes typed REST and realtime contract modules", () => {
    const contractsPath = resolve(projectRoot, "src/features/dashboard/types/contracts.ts");
    const realtimePath = resolve(projectRoot, "src/features/dashboard/types/realtime.ts");

    expect(existsSync(contractsPath)).toBe(true);
    expect(existsSync(realtimePath)).toBe(true);

    const contractsSource = sourceAt("src/features/dashboard/types/contracts.ts");
    const realtimeSource = sourceAt("src/features/dashboard/types/realtime.ts");

    expect(contractsSource).toContain("DashboardPrisonerSummary");
    expect(contractsSource).toContain("DashboardPrisonerDetailResponse");
    expect(realtimeSource).toContain("RealtimeEventName");
    expect(realtimeSource).toContain("DashboardRealtimeEnvelope");
  });

  it("provides baseline dashboard style and test setup artifacts", () => {
    const tokensPath = resolve(projectRoot, "src/styles/tokens.css");
    const setupPath = resolve(projectRoot, "src/test/setup.ts");

    expect(existsSync(tokensPath)).toBe(true);
    expect(existsSync(setupPath)).toBe(true);

    const tokensSource = sourceAt("src/styles/tokens.css");
    const setupSource = sourceAt("src/test/setup.ts");

    expect(tokensSource).toContain("--hc-color-bg");
    expect(tokensSource).toContain("--hc-severity-critical");
    expect(setupSource).toContain("beforeEach");
    expect(setupSource).toContain("afterEach");
  });
});

describe("dashboard API contract locks", () => {
  it("pins required prisoner list/detail fields", async () => {
    const contractModule = (await import("./contracts")) as {
      DASHBOARD_PRISONER_SUMMARY_REQUIRED_FIELDS?: readonly string[];
      DASHBOARD_PRISONER_DETAIL_REQUIRED_FIELDS?: readonly string[];
    };

    expect(contractModule.DASHBOARD_PRISONER_SUMMARY_REQUIRED_FIELDS).toEqual([
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
    ]);

    expect(contractModule.DASHBOARD_PRISONER_DETAIL_REQUIRED_FIELDS).toEqual([
      "prisoner",
      "protocol_history",
      "credentials",
      "commands",
      "downloads",
    ]);
  });

  it("fails fast when required summary/detail fields are missing", () => {
    const validSummary = {
      id: 14,
      source_ip: "203.0.113.10",
      country_code: "US",
      attempt_count: 7,
      first_seen_at: "2026-03-04T00:00:00Z",
      last_seen_at: "2026-03-04T00:10:00Z",
      credential_count: 2,
      command_count: 3,
      download_count: 1,
      enrichment: {
        status: "ready",
        last_updated_at: "2026-03-04T00:10:00Z",
        country_code: "US",
        asn: "AS13335",
        reputation_severity: "high",
      },
    };

    const missingSummaryField = {
      items: [{ ...validSummary, command_count: undefined }],
      next_cursor: null,
    };
    expect(() => parseDashboardPrisonerListResponse(missingSummaryField)).toThrow(
      "DashboardPrisonerListResponse.items[0].command_count",
    );

    const missingDetailField = {
      prisoner: {
        ...validSummary,
        enrichment: {
          status: "ready",
          last_updated_at: "2026-03-04T00:10:00Z",
          provider: "threat-intel",
          geo: { country_code: "US", asn: "AS13335" },
          reputation: { severity: "high", confidence: 91 },
          reason_metadata: { source: "provider" },
        },
      },
      protocol_history: [],
      credentials: [],
      commands: [],
    };
    expect(() => parseDashboardPrisonerDetailResponse(missingDetailField)).toThrow(
      "DashboardPrisonerDetailResponse.downloads",
    );
  });
});

describe("dashboard realtime contract locks", () => {
  it("matches backend websocket event literals exactly", () => {
    expect(DASHBOARD_REALTIME_EVENT_NAMES).toEqual([
      "welcome",
      "sync_start",
      "snapshot_chunk",
      "sync_complete",
      "new_prisoner",
      "prisoner_updated",
      "prisoner_enriched",
      "stats_update",
    ]);
  });
});
