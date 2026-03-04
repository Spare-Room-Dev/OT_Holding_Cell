import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import type { DashboardPrisonerDetailResponse } from "../types/contracts";
import { DetailPane } from "./detail-pane";

function buildDetailResponse(): DashboardPrisonerDetailResponse {
  return {
    prisoner: {
      id: 7,
      source_ip: "203.0.113.7",
      country_code: "AU",
      attempt_count: 18,
      first_seen_at: "2026-03-04T00:00:00Z",
      last_seen_at: "2026-03-04T00:45:00Z",
      credential_count: 2,
      command_count: 2,
      download_count: 1,
      enrichment: {
        status: "complete",
        last_updated_at: "2026-03-04T00:46:00Z",
        provider: "intel-provider",
        geo: {
          country_code: "AU",
          asn: "AS64000",
        },
        reputation: {
          severity: "high",
          confidence: 88,
        },
        reason_metadata: {
          reason: "<img src=x onerror=alert(1)>",
        },
      },
    },
    protocol_history: [
      {
        protocol: "ssh",
        attempt_count: 12,
        first_seen_at: "2026-03-04T00:00:00Z",
        last_seen_at: "2026-03-04T00:45:00Z",
      },
    ],
    credentials: [
      {
        protocol: "ssh",
        credential: "root:<script>alert('x')</script>",
        observed_at: "2026-03-04T00:15:00Z",
      },
    ],
    commands: [
      {
        protocol: "ssh",
        command: "<img src=x onerror=alert(2)>",
        observed_at: "2026-03-04T00:20:00Z",
      },
    ],
    downloads: [
      {
        protocol: "http",
        download_url: "http://malicious.example/payload.sh",
        observed_at: "2026-03-04T00:25:00Z",
      },
    ],
  };
}

describe("DetailPane", () => {
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
  });

  function renderPane(selectedPrisonerId: number | null, detail: DashboardPrisonerDetailResponse | null) {
    act(() => {
      root.render(<DetailPane selectedPrisonerId={selectedPrisonerId} detail={detail} />);
    });
  }

  it("shows explicit empty state when no prisoner is selected", () => {
    renderPane(null, null);
    expect(container.textContent).toContain("Select a prisoner from the list");
  });

  it("renders attack summary, intel context, activity timestamps, and keeps attacker values safe", () => {
    const detail = buildDetailResponse();
    renderPane(detail.prisoner.id, detail);

    const text = container.textContent ?? "";
    expect(text).toContain("Attack Summary");
    expect(text).toContain("Intel Context");
    expect(text).toContain("Activity Timeline");
    expect(text).toContain("First seen: 2026-03-04T00:00:00Z");
    expect(text).toContain("Last seen: 2026-03-04T00:45:00Z");
    expect(text).toContain("root:<script>alert('x')</script>");
    expect(text).toContain("<img src=x onerror=alert(2)>");
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
  });
});
