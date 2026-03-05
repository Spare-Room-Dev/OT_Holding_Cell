import { useEffect, useMemo, useRef, useState } from "react";
import { maskSourceIp } from "../domain/masking";
import { deriveSeverityFromPrisoner } from "../domain/severity";
import type { DashboardPrisonerSummary } from "../types/contracts";
import "./dashboard-layout.css";
import "./dashboard-surface-panels.css";

export const PRISONER_ROW_PULSE_MS = 700;

export interface PrisonerRowProps {
  prisoner: DashboardPrisonerSummary;
  isSelected?: boolean;
  onSelect?: (prisonerId: number) => void;
  className?: string;
}

function getEnrichmentFingerprint(prisoner: DashboardPrisonerSummary): string {
  return [
    prisoner.enrichment.status,
    prisoner.enrichment.last_updated_at ?? "none",
    prisoner.enrichment.reputation_severity ?? "none",
    prisoner.enrichment.country_code ?? "none",
    prisoner.enrichment.asn ?? "none",
  ].join("|");
}

function formatValue(value: string | null): string {
  return value ?? "Unknown";
}

export function PrisonerRow({ prisoner, isSelected = false, onSelect, className }: PrisonerRowProps) {
  const severity = useMemo(
    () =>
      deriveSeverityFromPrisoner({
        attempt_count: prisoner.attempt_count,
        enrichment: prisoner.enrichment,
      }),
    [prisoner.attempt_count, prisoner.enrichment],
  );
  const enrichmentFingerprint = getEnrichmentFingerprint(prisoner);
  const previousSeverityRef = useRef(severity.tier);
  const previousFingerprintRef = useRef(enrichmentFingerprint);
  const timeoutRef = useRef<number | null>(null);
  const [isPulsing, setIsPulsing] = useState(false);

  useEffect(
    () => () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    const severityChanged = previousSeverityRef.current !== severity.tier;
    const enrichmentChanged = previousFingerprintRef.current !== enrichmentFingerprint;

    if (severityChanged && enrichmentChanged) {
      setIsPulsing(true);

      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = window.setTimeout(() => {
        setIsPulsing(false);
        timeoutRef.current = null;
      }, PRISONER_ROW_PULSE_MS);
    }

    previousSeverityRef.current = severity.tier;
    previousFingerprintRef.current = enrichmentFingerprint;
  }, [severity.tier, enrichmentFingerprint]);

  const rowClassName = [
    "prisoner-row",
    "surface-card",
    "surface-card--row",
    isSelected ? "prisoner-row--selected" : "",
    isPulsing ? "prisoner-row--pulse" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type="button"
      className={rowClassName}
      onClick={() => onSelect?.(prisoner.id)}
      aria-pressed={isSelected}
      data-prisoner-id={prisoner.id}
    >
      <div className="prisoner-row__top">
        <strong className="prisoner-row__ip surface-mono">{maskSourceIp(prisoner.source_ip)}</strong>
        <span
          className={`prisoner-row__severity-badge surface-chip surface-chip--severity prisoner-row__severity-badge--${severity.tier}`}
        >
          {severity.label}
        </span>
      </div>

      <p className="prisoner-row__summary surface-readout">
        Attempts: {prisoner.attempt_count} | Credentials: {prisoner.credential_count} | Commands: {prisoner.command_count} |
        Downloads: {prisoner.download_count}
      </p>

      <p className="prisoner-row__intel surface-readout">
        Country: {formatValue(prisoner.country_code ?? prisoner.enrichment.country_code)} | Enrichment:{" "}
        {prisoner.enrichment.status}
      </p>

      <p className="prisoner-row__intel surface-readout">
        <span className="prisoner-row__signal surface-tactical-label">Signal: {severity.signal}</span> | Attempt band:{" "}
        {severity.attemptBand}
      </p>

      <p className="prisoner-row__timestamps surface-readout">
        First seen: {prisoner.first_seen_at} | Last seen: {prisoner.last_seen_at}
      </p>
    </button>
  );
}
