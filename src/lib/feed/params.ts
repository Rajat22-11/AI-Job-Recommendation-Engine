import {
  FEED_STATUSES,
  isOneOf,
  LOCATION_BUCKETS,
  ROLE_TRACKS,
  WORK_MODES,
  type FeedStatus,
  type LocationBucket,
  type RoleTrack,
  type WorkMode,
} from "@/lib/db/domain";

export const PAGE_SIZE = 25;

export const SALARY_FILTERS = ["any", "meets", "unknown"] as const;
export type SalaryFilter = (typeof SALARY_FILTERS)[number];

export const POSTED_WITHIN = [1, 3, 7, 30] as const;
export type PostedWithin = (typeof POSTED_WITHIN)[number];

export const SORTS = ["fit", "newest", "salary"] as const;
export type FeedSort = (typeof SORTS)[number];

export const SORT_LABELS: Record<FeedSort, string> = {
  fit: "Best fit",
  newest: "Newest",
  salary: "Salary",
};

export const SOURCE_ID_PATTERN = /^[a-z0-9_-]{2,40}$/;
const MAX_QUERY_LENGTH = 100;

export interface FeedFilters {
  track: RoleTrack[];
  loc: LocationBucket[];
  mode: WorkMode[];
  status: FeedStatus[] | "all";
  source: string[];
  fit: number;
  salary: SalaryFilter;
  posted: PostedWithin | null;
  seen24h: boolean;
  q: string;
  sort: FeedSort;
  page: number;
}

export const DEFAULT_STATUSES: FeedStatus[] = ["new", "saved"];
export const DEFAULT_FIT = 3;

export const DEFAULT_FILTERS: FeedFilters = {
  track: [],
  loc: [],
  mode: [],
  status: DEFAULT_STATUSES,
  source: [],
  fit: DEFAULT_FIT,
  salary: "any",
  posted: null,
  seen24h: false,
  q: "",
  sort: "fit",
  page: 1,
};

export type RawSearchParams = Record<string, string | string[] | undefined>;

function all(raw: RawSearchParams, key: string): string[] {
  const value = raw[key];
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function first(raw: RawSearchParams, key: string): string | undefined {
  return all(raw, key)[0];
}

function validValues<T extends string>(
  values: readonly T[],
  given: string[],
): T[] {
  return [...new Set(given.filter((v): v is T => isOneOf(values, v)))];
}

function intIn(
  value: string | undefined,
  min: number,
  max: number,
): number | null {
  if (value === undefined || !/^\d+$/.test(value)) return null;
  const n = Number(value);
  return n >= min && n <= max ? n : null;
}

/** URL search params → filters. Invalid values are dropped; absent ones default. */
export function parseFeedParams(raw: RawSearchParams): FeedFilters {
  const statuses = all(raw, "status");
  let status: FeedFilters["status"] = DEFAULT_STATUSES;
  if (statuses.includes("all")) {
    status = "all";
  } else {
    const valid = validValues(FEED_STATUSES, statuses);
    if (valid.length > 0) status = valid;
  }

  const posted = intIn(first(raw, "posted"), 1, 30);
  const salary = first(raw, "salary");
  const sort = first(raw, "sort");

  return {
    track: validValues(ROLE_TRACKS, all(raw, "track")),
    loc: validValues(LOCATION_BUCKETS, all(raw, "loc")),
    mode: validValues(WORK_MODES, all(raw, "mode")),
    status,
    source: [
      ...new Set(all(raw, "source").filter((s) => SOURCE_ID_PATTERN.test(s))),
    ],
    fit: intIn(first(raw, "fit"), 0, 5) ?? DEFAULT_FIT,
    salary: isOneOf(SALARY_FILTERS, salary) ? salary : "any",
    posted: (POSTED_WITHIN as readonly number[]).includes(posted ?? -1)
      ? (posted as PostedWithin)
      : null,
    seen24h: first(raw, "seen") === "24h",
    q: (first(raw, "q") ?? "").trim().slice(0, MAX_QUERY_LENGTH),
    sort: isOneOf(SORTS, sort) ? sort : "fit",
    page: intIn(first(raw, "page"), 1, 100_000) ?? 1,
  };
}

function sameSet(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((v) => b.includes(v));
}

/** Filters → query string ("" or "?..."), omitting defaults to keep URLs short. */
export function serializeFeedParams(filters: FeedFilters): string {
  const params = new URLSearchParams();
  for (const v of filters.track) params.append("track", v);
  for (const v of filters.loc) params.append("loc", v);
  for (const v of filters.mode) params.append("mode", v);
  if (filters.status === "all") {
    params.append("status", "all");
  } else if (!sameSet(filters.status, DEFAULT_STATUSES)) {
    for (const v of filters.status) params.append("status", v);
  }
  for (const v of filters.source) params.append("source", v);
  if (filters.fit !== DEFAULT_FIT) params.set("fit", String(filters.fit));
  if (filters.salary !== "any") params.set("salary", filters.salary);
  if (filters.posted !== null) params.set("posted", String(filters.posted));
  if (filters.seen24h) params.set("seen", "24h");
  if (filters.q) params.set("q", filters.q);
  if (filters.sort !== "fit") params.set("sort", filters.sort);
  if (filters.page > 1) params.set("page", String(filters.page));
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** Feed URL for filters with some fields changed. Filter changes reset to page 1. */
export function feedHref(
  filters: FeedFilters,
  changes: Partial<FeedFilters> = {},
): string {
  const page = "page" in changes ? (changes.page ?? 1) : 1;
  return `/${serializeFeedParams({ ...filters, ...changes, page })}`;
}

/** Number of filters that differ from the default view (sort and page excluded). */
export function activeFilterCount(filters: FeedFilters): number {
  const d = DEFAULT_FILTERS;
  return [
    filters.track.length > 0,
    filters.loc.length > 0,
    filters.mode.length > 0,
    filters.status === "all" ||
      (d.status !== "all" && !sameSet(filters.status, d.status)),
    filters.source.length > 0,
    filters.fit !== d.fit,
    filters.salary !== d.salary,
    filters.posted !== null,
    filters.seen24h,
    filters.q !== "",
  ].filter(Boolean).length;
}

/** A `from` value from the detail page, accepted only if it is a feed query. */
export function safeFeedQuery(from: unknown): string {
  if (typeof from !== "string" || (from !== "" && !from.startsWith("?")))
    return "";
  const parsed = parseFeedParams(Object.fromEntries(groupParams(from)));
  return serializeFeedParams(parsed);
}

function groupParams(query: string): Map<string, string[]> {
  const grouped = new Map<string, string[]>();
  for (const [key, value] of new URLSearchParams(query)) {
    grouped.set(key, [...(grouped.get(key) ?? []), value]);
  }
  return grouped;
}

/**
 * The canonical query ("" or "?...") for a filter form's current values.
 * Goes through the same parser as the URL, so the result is what the server
 * will see, and `page` is always dropped.
 */
export function feedQueryFromForm(data: FormData): string {
  const raw: Record<string, string[]> = {};
  for (const [key, value] of data.entries()) {
    if (typeof value === "string") (raw[key] ??= []).push(value);
  }
  return serializeFeedParams({ ...parseFeedParams(raw), page: 1 });
}
