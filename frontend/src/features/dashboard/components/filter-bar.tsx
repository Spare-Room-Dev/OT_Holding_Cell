import type { DashboardTimeWindow } from "../state/filter-pipeline";
import "./dashboard-layout.css";

const TIME_WINDOW_OPTIONS: Array<{ value: DashboardTimeWindow; label: string }> = [
  { value: "15m", label: "Last 15 minutes" },
  { value: "1h", label: "Last 1 hour" },
  { value: "24h", label: "Last 24 hours" },
  { value: "all", label: "All activity" },
];

export interface FilterBarProps {
  country: string | null;
  timeWindow: DashboardTimeWindow;
  countryOptions: string[];
  filteredOutCount: number;
  onCountryChange: (country: string | null) => void;
  onTimeWindowChange: (timeWindow: DashboardTimeWindow) => void;
}

export function FilterBar({
  country,
  timeWindow,
  countryOptions,
  filteredOutCount,
  onCountryChange,
  onTimeWindowChange,
}: FilterBarProps) {
  return (
    <section className="dashboard-panel dashboard-shell__filters-band" aria-label="Filters">
      <div className="filter-bar filter-bar--command-band">
        <label className="filter-bar__control">
          <span className="filter-bar__label command-band__label">Country</span>
          <select
            className="filter-bar__select"
            value={country ?? ""}
            onChange={(event) => onCountryChange(event.target.value === "" ? null : event.target.value)}
          >
            <option value="">All countries</option>
            {countryOptions.map((countryOption) => (
              <option key={countryOption} value={countryOption}>
                {countryOption}
              </option>
            ))}
          </select>
        </label>

        <label className="filter-bar__control">
          <span className="filter-bar__label command-band__label">Time window</span>
          <select
            className="filter-bar__select"
            value={timeWindow}
            onChange={(event) => onTimeWindowChange(event.target.value as DashboardTimeWindow)}
          >
            {TIME_WINDOW_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <p className="filter-bar__meta command-band__meta" aria-live="polite">
          Filtered out: {filteredOutCount}
        </p>
      </div>
    </section>
  );
}
