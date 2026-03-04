import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DashboardPrisonerSummary } from "../types/contracts";
import { PRISONER_ROW_PULSE_MS, PrisonerRow } from "./prisoner-row";

function buildPrisoner(overrides: Partial<DashboardPrisonerSummary> = {}): DashboardPrisonerSummary {
  const { enrichment: enrichmentOverrides, ...rowOverrides } = overrides;
  const baseEnrichment = {
    status: "pending",
    last_updated_at: null,
    country_code: "US",
    asn: "AS12345",
    reputation_severity: null,
  } as const;
  const basePrisoner: DashboardPrisonerSummary = {
    id: 44,
    source_ip: "198.51.100.44",
    country_code: "US",
    attempt_count: 4,
    first_seen_at: "2026-03-04T00:00:00Z",
    last_seen_at: "2026-03-04T01:00:00Z",
    credential_count: 1,
    command_count: 2,
    download_count: 1,
    enrichment: {
      ...baseEnrichment,
    },
  };

  return {
    ...basePrisoner,
    ...rowOverrides,
    enrichment: {
      ...baseEnrichment,
      ...enrichmentOverrides,
    },
  };
}

describe("PrisonerRow", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    vi.useRealTimers();
  });

  function renderRow(prisoner: DashboardPrisonerSummary) {
    act(() => {
      root.render(<PrisonerRow prisoner={prisoner} />);
    });
  }

  it("renders masked source ip and non-color severity cues", () => {
    renderRow(
      buildPrisoner({
        source_ip: "198.51.100.44",
        attempt_count: 25,
        enrichment: {
          status: "complete",
          last_updated_at: "2026-03-04T01:01:00Z",
          country_code: "US",
          asn: "AS12345",
          reputation_severity: "critical",
        },
      }),
    );

    const text = container.textContent ?? "";
    expect(text).toContain("198.51.x.x");
    expect(text).toContain("Critical");
    expect(text).toContain("Signal: incident");
    expect(text).toContain("Attempt band: storm");
  });

  it("pulses once for enrichment-style severity changes then returns to steady state", () => {
    vi.useFakeTimers();

    const pendingPrisoner = buildPrisoner({
      attempt_count: 12,
      enrichment: {
        status: "pending",
        last_updated_at: null,
        country_code: "US",
        asn: "AS12345",
        reputation_severity: null,
      },
    });
    renderRow(pendingPrisoner);
    let row = container.querySelector(".prisoner-row");
    expect(row?.classList.contains("prisoner-row--pulse")).toBe(false);

    const enrichedPrisoner = buildPrisoner({
      attempt_count: 12,
      enrichment: {
        status: "complete",
        last_updated_at: "2026-03-04T01:05:00Z",
        country_code: "US",
        asn: "AS12345",
        reputation_severity: "high",
      },
    });
    renderRow(enrichedPrisoner);
    row = container.querySelector(".prisoner-row");
    expect(row?.classList.contains("prisoner-row--pulse")).toBe(true);

    act(() => {
      vi.advanceTimersByTime(PRISONER_ROW_PULSE_MS + 10);
    });

    row = container.querySelector(".prisoner-row");
    expect(row?.classList.contains("prisoner-row--pulse")).toBe(false);

    renderRow({
      ...enrichedPrisoner,
      command_count: enrichedPrisoner.command_count + 1,
    });
    row = container.querySelector(".prisoner-row");
    expect(row?.classList.contains("prisoner-row--pulse")).toBe(false);
  });
});
