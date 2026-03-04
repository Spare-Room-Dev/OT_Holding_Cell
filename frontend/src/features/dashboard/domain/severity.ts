import type { DashboardPrisonerEnrichmentSummary, DashboardPrisonerSummary } from "../types/contracts";

export type SeverityTier = "low" | "caution" | "high" | "critical";
export type SeveritySignal = "monitor" | "watchlist" | "escalate" | "incident";

export interface SeverityDescriptor {
  tier: SeverityTier;
  label: string;
  signal: SeveritySignal;
  attemptBand: "single" | "burst" | "sustained" | "storm";
}

interface DeriveSeverityInput {
  attemptCount: number;
  enrichmentStatus: string;
  reputationSeverity: string | null;
}

const TIER_ORDER: SeverityTier[] = ["low", "caution", "high", "critical"];

const TIER_DESCRIPTORS: Record<SeverityTier, SeverityDescriptor> = {
  low: {
    tier: "low",
    label: "Low",
    signal: "monitor",
    attemptBand: "single",
  },
  caution: {
    tier: "caution",
    label: "Caution",
    signal: "watchlist",
    attemptBand: "burst",
  },
  high: {
    tier: "high",
    label: "High",
    signal: "escalate",
    attemptBand: "sustained",
  },
  critical: {
    tier: "critical",
    label: "Critical",
    signal: "incident",
    attemptBand: "storm",
  },
};

function normalizeAttemptCount(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.floor(value));
}

function deriveAttemptTier(attemptCount: number): SeverityTier {
  if (attemptCount >= 20) {
    return "critical";
  }
  if (attemptCount >= 10) {
    return "high";
  }
  if (attemptCount >= 5) {
    return "caution";
  }
  return "low";
}

function normalizeTier(value: string | null): SeverityTier | null {
  if (value === null) {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (normalized === "critical") {
    return "critical";
  }
  if (normalized === "high") {
    return "high";
  }
  if (normalized === "medium" || normalized === "moderate" || normalized === "caution") {
    return "caution";
  }
  if (normalized === "low" || normalized === "info" || normalized === "none") {
    return "low";
  }

  return null;
}

function pickHigherTier(a: SeverityTier, b: SeverityTier): SeverityTier {
  const aIndex = TIER_ORDER.indexOf(a);
  const bIndex = TIER_ORDER.indexOf(b);
  return aIndex >= bIndex ? a : b;
}

export function deriveSeverity(input: DeriveSeverityInput): SeverityDescriptor {
  const attemptCount = normalizeAttemptCount(input.attemptCount);
  const enrichmentStatus = input.enrichmentStatus.trim().toLowerCase();

  if (enrichmentStatus === "pending" || enrichmentStatus === "failed") {
    return TIER_DESCRIPTORS.caution;
  }

  const attemptTier = deriveAttemptTier(attemptCount);
  const reputationTier = normalizeTier(input.reputationSeverity);
  const tier = reputationTier === null ? attemptTier : pickHigherTier(attemptTier, reputationTier);

  return TIER_DESCRIPTORS[tier];
}

export function deriveSeverityFromPrisoner(
  prisoner: Pick<DashboardPrisonerSummary, "attempt_count" | "enrichment">,
): SeverityDescriptor {
  return deriveSeverity({
    attemptCount: prisoner.attempt_count,
    enrichmentStatus: prisoner.enrichment.status,
    reputationSeverity: prisoner.enrichment.reputation_severity,
  });
}

export function deriveSeverityFromEnrichmentDetail(
  attemptCount: number,
  enrichment: Pick<DashboardPrisonerEnrichmentSummary, "status" | "reputation_severity">,
): SeverityDescriptor {
  return deriveSeverity({
    attemptCount,
    enrichmentStatus: enrichment.status,
    reputationSeverity: enrichment.reputation_severity,
  });
}
