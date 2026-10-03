import {
  LOCATION_BUCKET_LABELS,
  ROLE_TRACK_LABELS,
  STATUS_LABELS,
  WORK_MODE_LABELS,
} from "@/lib/db/domain";
import {
  DEFAULT_FILTERS,
  DEFAULT_STATUSES,
  feedHref,
  type FeedFilters,
} from "@/lib/feed/params";

export interface FilterChip {
  key: string;
  label: string;
  /** Feed URL with just this filter value removed. */
  href: string;
}

const SALARY_CHIPS = {
  meets: "Meets my minimum",
  unknown: "Salary not disclosed",
} as const;

/** One chip per active non-default filter value. Sort and page never get one. */
export function activeFilterChips(
  filters: FeedFilters,
  sourceNames: ReadonlyMap<string, string>,
): FilterChip[] {
  const chips: FilterChip[] = [];
  const add = (key: string, label: string, changes: Partial<FeedFilters>) =>
    chips.push({ key, label, href: feedHref(filters, changes) });
  const without = <T>(values: readonly T[], value: T) =>
    values.filter((v) => v !== value);

  if (filters.q) add("q", `"${filters.q}"`, { q: "" });

  if (filters.status === "all") {
    add("status:all", "Any status", { status: DEFAULT_STATUSES });
  } else if (
    filters.status.length !== DEFAULT_STATUSES.length ||
    !filters.status.every((s) => DEFAULT_STATUSES.includes(s))
  ) {
    for (const s of filters.status) {
      add(`status:${s}`, STATUS_LABELS[s], {
        status: without(filters.status, s),
      });
    }
  }

  for (const v of filters.track) {
    add(`track:${v}`, ROLE_TRACK_LABELS[v], {
      track: without(filters.track, v),
    });
  }
  for (const v of filters.loc) {
    add(`loc:${v}`, LOCATION_BUCKET_LABELS[v], {
      loc: without(filters.loc, v),
    });
  }
  for (const v of filters.mode) {
    add(`mode:${v}`, WORK_MODE_LABELS[v], { mode: without(filters.mode, v) });
  }
  for (const v of filters.source) {
    add(`source:${v}`, sourceNames.get(v) ?? v, {
      source: without(filters.source, v),
    });
  }

  if (filters.fit !== DEFAULT_FILTERS.fit) {
    add("fit", filters.fit === 0 ? "Any fit" : `Fit ${filters.fit}+`, {
      fit: DEFAULT_FILTERS.fit,
    });
  }
  if (filters.salary !== "any") {
    add("salary", SALARY_CHIPS[filters.salary], { salary: "any" });
  }
  if (filters.posted !== null) {
    add(
      "posted",
      filters.posted === 1
        ? "Posted in 1 day"
        : `Posted in ${filters.posted} days`,
      { posted: null },
    );
  }
  if (filters.seen24h) add("seen", "New today", { seen24h: false });

  return chips;
}
