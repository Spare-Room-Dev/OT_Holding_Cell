import { SafeRender } from "../domain/safe-render";
import { maskSourceIp } from "../domain/masking";
import { deriveSeverity } from "../domain/severity";
import type {
  DashboardPrisonerCommandHistoryEntry,
  DashboardPrisonerCredentialHistoryEntry,
  DashboardPrisonerDetailResponse,
  DashboardPrisonerDownloadHistoryEntry,
  DashboardPrisonerProtocolHistoryEntry,
} from "../types/contracts";
import "./dashboard-layout.css";
import "./dashboard-surface-panels.css";

export interface DetailPaneProps {
  selectedPrisonerId: number | null;
  detail: DashboardPrisonerDetailResponse | null;
}

function renderProtocolHistoryItem(entry: DashboardPrisonerProtocolHistoryEntry): string {
  return `${entry.protocol} - attempts ${entry.attempt_count} (${entry.first_seen_at} to ${entry.last_seen_at})`;
}

function renderCredentialItem(entry: DashboardPrisonerCredentialHistoryEntry): string {
  return `${entry.protocol} credential @ ${entry.observed_at}: ${entry.credential}`;
}

function renderCommandItem(entry: DashboardPrisonerCommandHistoryEntry): string {
  return `${entry.protocol} command @ ${entry.observed_at}: ${entry.command}`;
}

function renderDownloadItem(entry: DashboardPrisonerDownloadHistoryEntry): string {
  return `${entry.protocol} download @ ${entry.observed_at}: ${entry.download_url}`;
}

function renderItemList(items: string[]) {
  if (items.length === 0) {
    return <p className="detail-pane__line surface-section__line">No records available.</p>;
  }

  return (
    <ul className="detail-pane__list surface-section__list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="detail-pane__list-item surface-section__list-item">
          <SafeRender value={item} />
        </li>
      ))}
    </ul>
  );
}

function renderReasonMetadata(reasonMetadata: Record<string, string>) {
  const entries = Object.entries(reasonMetadata);
  if (entries.length === 0) {
    return <p className="detail-pane__line surface-section__line">Reason metadata: none</p>;
  }

  return (
    <ul className="detail-pane__list surface-section__list">
      {entries.map(([key, value]) => (
        <li key={key} className="detail-pane__list-item surface-section__list-item">
          <SafeRender value={`${key}: ${value}`} />
        </li>
      ))}
    </ul>
  );
}

export function DetailPane({ selectedPrisonerId, detail }: DetailPaneProps) {
  if (selectedPrisonerId === null) {
    return (
      <aside
        className="dashboard-panel surface-panel surface-panel--detail surface-panel--detail-empty detail-pane detail-pane--empty"
        aria-live="polite"
        data-command-center-region="dossier-pane"
      >
        <h2 className="dashboard-panel__title" data-command-center-heading="panel-title">
          Prisoner Detail
        </h2>
        <p className="detail-pane__empty-text">Select a prisoner from the list to inspect attack summary and activity.</p>
      </aside>
    );
  }

  if (detail === null) {
    return (
      <aside
        className="dashboard-panel surface-panel surface-panel--detail detail-pane"
        aria-live="polite"
        data-command-center-region="dossier-pane"
      >
        <h2 className="dashboard-panel__title" data-command-center-heading="panel-title">
          Prisoner Detail
        </h2>
        <p className="detail-pane__line">Loading selected prisoner detail...</p>
      </aside>
    );
  }

  const severity = deriveSeverity({
    attemptCount: detail.prisoner.attempt_count,
    enrichmentStatus: detail.prisoner.enrichment.status,
    reputationSeverity: detail.prisoner.enrichment.reputation.severity,
  });
  const maskedSourceIp = maskSourceIp(detail.prisoner.source_ip);

  return (
    <aside
      className="dashboard-panel surface-panel surface-panel--detail detail-pane"
      aria-live="polite"
      data-command-center-region="dossier-pane"
    >
      <header className="surface-panel__header">
        <h2 className="dashboard-panel__title surface-panel__title" data-command-center-heading="panel-title">
          Prisoner Detail
        </h2>
        <p className="dashboard-panel__subtitle">
          Severity {severity.label} | Signal {severity.signal}
        </p>
      </header>

      <section className="detail-pane__section surface-section" aria-label="Attack summary">
        <h3 className="detail-pane__section-title surface-section__title">Attack Summary</h3>
        <p className="detail-pane__line surface-section__line">
          Source IP: <SafeRender value={maskedSourceIp} />
        </p>
        <p className="detail-pane__line surface-section__line">Country: {detail.prisoner.country_code ?? "Unknown"}</p>
        <p className="detail-pane__line surface-section__line">Attempts: {detail.prisoner.attempt_count}</p>
        <p className="detail-pane__line surface-section__line">Credentials observed: {detail.prisoner.credential_count}</p>
        <p className="detail-pane__line surface-section__line">Commands observed: {detail.prisoner.command_count}</p>
        <p className="detail-pane__line surface-section__line">Downloads observed: {detail.prisoner.download_count}</p>
        <p className="detail-pane__line surface-section__line">First seen: {detail.prisoner.first_seen_at}</p>
        <p className="detail-pane__line surface-section__line">Last seen: {detail.prisoner.last_seen_at}</p>
      </section>

      <section className="detail-pane__section surface-section" aria-label="Intel context">
        <h3 className="detail-pane__section-title surface-section__title">Intel Context</h3>
        <p className="detail-pane__line surface-section__line">Status: {detail.prisoner.enrichment.status}</p>
        <p className="detail-pane__line surface-section__line">Provider: {detail.prisoner.enrichment.provider ?? "Unknown"}</p>
        <p className="detail-pane__line surface-section__line">
          Geo country: {detail.prisoner.enrichment.geo.country_code ?? "Unknown"}
        </p>
        <p className="detail-pane__line surface-section__line">ASN: {detail.prisoner.enrichment.geo.asn ?? "Unknown"}</p>
        <p className="detail-pane__line surface-section__line">
          Reputation: {detail.prisoner.enrichment.reputation.severity ?? "Unknown"} (confidence{" "}
          {detail.prisoner.enrichment.reputation.confidence ?? "unknown"})
        </p>
        <p className="detail-pane__line surface-section__line">
          Last updated: {detail.prisoner.enrichment.last_updated_at ?? "Unknown"}
        </p>
        {renderReasonMetadata(detail.prisoner.enrichment.reason_metadata)}
      </section>

      <section className="detail-pane__section surface-section" aria-label="Activity timeline">
        <h3 className="detail-pane__section-title surface-section__title">Activity Timeline</h3>
        <p className="detail-pane__line surface-section__line surface-tactical-label">Protocol history</p>
        {renderItemList(detail.protocol_history.map(renderProtocolHistoryItem))}
        <p className="detail-pane__line surface-section__line surface-tactical-label">Credentials</p>
        {renderItemList(detail.credentials.map(renderCredentialItem))}
        <p className="detail-pane__line surface-section__line surface-tactical-label">Commands</p>
        {renderItemList(detail.commands.map(renderCommandItem))}
        <p className="detail-pane__line surface-section__line surface-tactical-label">Downloads</p>
        {renderItemList(detail.downloads.map(renderDownloadItem))}
      </section>
    </aside>
  );
}
