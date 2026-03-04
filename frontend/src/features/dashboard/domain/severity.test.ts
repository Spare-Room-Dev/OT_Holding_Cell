import { describe, expect, it } from "vitest";
import { deriveSeverity } from "./severity";

describe("deriveSeverity", () => {
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
});
