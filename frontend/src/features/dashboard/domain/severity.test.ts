import { describe, expect, it } from "vitest";
import { deriveSeverity } from "./severity";

describe("deriveSeverity", () => {
  it("maps failed enrichment to caution baseline", () => {
    const severity = deriveSeverity({
      attemptCount: 25,
      enrichmentStatus: "failed",
      reputationSeverity: "critical",
    });

    expect(severity.tier).toBe("caution");
    expect(severity.label).toBe("Caution");
    expect(severity.signal).toBe("watchlist");
  });

  it("maps pending enrichment to caution baseline", () => {
    const severity = deriveSeverity({
      attemptCount: 25,
      enrichmentStatus: "pending",
      reputationSeverity: "critical",
    });

    expect(severity.tier).toBe("caution");
    expect(severity.label).toBe("Caution");
    expect(severity.signal).toBe("watchlist");
  });

  it("uses deterministic attempt thresholds when enrichment is complete", () => {
    expect(
      deriveSeverity({
        attemptCount: 4,
        enrichmentStatus: "complete",
        reputationSeverity: null,
      }).tier,
    ).toBe("low");
    expect(
      deriveSeverity({
        attemptCount: 5,
        enrichmentStatus: "complete",
        reputationSeverity: null,
      }).tier,
    ).toBe("caution");
    expect(
      deriveSeverity({
        attemptCount: 10,
        enrichmentStatus: "complete",
        reputationSeverity: null,
      }).tier,
    ).toBe("high");
    expect(
      deriveSeverity({
        attemptCount: 20,
        enrichmentStatus: "complete",
        reputationSeverity: null,
      }).tier,
    ).toBe("critical");
  });

  it("elevates tier when reputation severity is higher than attempt-derived tier", () => {
    const severity = deriveSeverity({
      attemptCount: 3,
      enrichmentStatus: "complete",
      reputationSeverity: "high",
    });

    expect(severity.tier).toBe("high");
    expect(severity.signal).toBe("escalate");
  });

  it("does not downgrade tier when reputation severity is lower than attempt-derived tier", () => {
    const severity = deriveSeverity({
      attemptCount: 21,
      enrichmentStatus: "complete",
      reputationSeverity: "low",
    });

    expect(severity.tier).toBe("critical");
    expect(severity.signal).toBe("incident");
  });
});
