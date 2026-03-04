export type PrisonerListFilters = {
  country: string | null;
};

function normalizeCountry(country: string | null | undefined): string | null {
  if (country === null || country === undefined) {
    return null;
  }
  const trimmed = country.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export const dashboardQueryKeys = {
  dashboard: ["dashboard"] as const,
  prisoners: {
    all: ["dashboard", "prisoners"] as const,
    list: (filters: PrisonerListFilters) =>
      ["dashboard", "prisoners", "list", { country: normalizeCountry(filters.country) }] as const,
    detail: (prisonerId: number | null) => ["dashboard", "prisoners", "detail", prisonerId] as const,
  },
} as const;
