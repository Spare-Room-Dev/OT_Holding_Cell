import type { DashboardPrisonerSummary } from "../types/contracts";
import { PrisonerRow } from "./prisoner-row";
import "./dashboard-layout.css";

export interface PrisonerListProps {
  prisoners: DashboardPrisonerSummary[];
  selectedPrisonerId: number | null;
  onSelectPrisoner?: (prisonerId: number) => void;
  filteredOutCount?: number;
}

export function PrisonerList({
  prisoners,
  selectedPrisonerId,
  onSelectPrisoner,
  filteredOutCount = 0,
}: PrisonerListProps) {
  return (
    <section className="dashboard-panel prisoner-list" aria-label="Prisoner list">
      <header>
        <h2 className="dashboard-panel__title">Active Prisoners</h2>
        <p className="dashboard-panel__subtitle">
          Visible: {prisoners.length}
          {filteredOutCount > 0 ? ` | Filtered out: ${filteredOutCount}` : ""}
        </p>
      </header>

      {prisoners.length === 0 ? (
        <p className="prisoner-list__empty">No prisoners are visible for the selected filters.</p>
      ) : (
        <ul className="prisoner-list__items">
          {prisoners.map((prisoner) => (
            <li key={prisoner.id}>
              <PrisonerRow
                prisoner={prisoner}
                isSelected={selectedPrisonerId === prisoner.id}
                onSelect={onSelectPrisoner}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
