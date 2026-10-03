import "server-only";
import { db } from "@/lib/db/client";
import { toFeedJob, UUID_PATTERN, type FeedJob } from "@/lib/db/jobs";
import {
  hidesSkipped,
  NEW_TODAY_FILTERS,
  PAGE_SIZE,
  type FeedFilters,
} from "@/lib/feed/params";
import {
  postedFilter,
  sanitizeSearch,
  searchFilter,
  sourceFilter,
} from "@/lib/feed/query-filters";

const DAY_MS = 24 * 60 * 60 * 1000;
// PostgREST answers "range not satisfiable" for an offset past the last row.
const RANGE_NOT_SATISFIABLE = "PGRST103";

function filteredFeed(filters: FeedFilters, head: boolean) {
  let query = db()
    .from("job_feed")
    .select("*", { count: "exact", head })
    .eq("is_active", true);

  if (filters.track.length) query = query.in("role_track", filters.track);
  if (filters.loc.length) query = query.in("location_bucket", filters.loc);
  if (filters.mode.length) query = query.in("work_mode", filters.mode);
  if (filters.status !== "all") query = query.in("app_status", filters.status);
  if (filters.fit > 0) query = query.gte("fit_score", filters.fit);
  if (filters.salary === "meets") query = query.eq("salary_meets_min", true);
  if (filters.salary === "unknown") query = query.is("salary_meets_min", null);
  // These two mirror salaryState() in src/lib/format.ts.
  if (filters.salary === "not_disclosed") {
    query = query
      .or("salary_text.is.null,salary_text.eq.")
      .is("salary_min_lpa", null)
      .is("salary_max_lpa", null);
  }
  if (filters.salary === "unparsed") {
    query = query
      .is("salary_meets_min", null)
      .or(
        "salary_text.neq.,salary_min_lpa.not.is.null,salary_max_lpa.not.is.null",
      );
  }
  if (filters.seen24h) {
    query = query.gte(
      "first_seen_at",
      new Date(Date.now() - DAY_MS).toISOString(),
    );
  }
  // Separate or() calls are ANDed together by PostgREST.
  if (filters.source.length) query = query.or(sourceFilter(filters.source));
  if (filters.posted !== null) query = query.or(postedFilter(filters.posted));
  const term = sanitizeSearch(filters.q);
  if (term) query = query.or(searchFilter(term));

  return query;
}

export interface FeedPage {
  jobs: FeedJob[];
  total: number;
}

export async function getFeedPage(filters: FeedFilters): Promise<FeedPage> {
  const from = (filters.page - 1) * PAGE_SIZE;
  const desc = { ascending: false, nullsFirst: false } as const;

  let query = filteredFeed(filters, false);
  if (filters.sort === "fit") {
    query = query
      .order("fit_score", desc)
      .order("posted_at", desc)
      .order("first_seen_at", desc);
  } else if (filters.sort === "newest") {
    query = query.order("posted_at", desc).order("first_seen_at", desc);
  } else {
    query = query
      .order("salary_max_lpa", desc)
      .order("salary_min_lpa", desc)
      .order("fit_score", desc);
  }

  const { data, count, error } = await query
    .order("id")
    .range(from, from + PAGE_SIZE - 1);

  if (error?.code === RANGE_NOT_SATISFIABLE) {
    const { count: total, error: countError } = await filteredFeed(
      filters,
      true,
    );
    if (countError) throw countError;
    return { jobs: [], total: total ?? 0 };
  }
  if (error) throw error;
  return { jobs: data.map(toFeedJob), total: count ?? 0 };
}

/** Exactly the jobs NEW_TODAY_HREF lists: still new, any fit, any other filter. */
export async function countNewToday(): Promise<number> {
  const { count, error } = await filteredFeed(NEW_TODAY_FILTERS, true);
  if (error) throw error;
  return count ?? 0;
}

/**
 * Skipped jobs the current filters would otherwise show, or null when the
 * status filter already includes them.
 */
export async function countHiddenSkipped(
  filters: FeedFilters,
): Promise<number | null> {
  if (!hidesSkipped(filters)) return null;
  const { count, error } = await filteredFeed(
    { ...filters, status: ["skipped"] },
    true,
  );
  if (error) throw error;
  return count ?? 0;
}

export async function getJob(id: string): Promise<FeedJob | null> {
  if (!UUID_PATTERN.test(id)) return null;
  const { data, error } = await db()
    .from("job_feed")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return data ? toFeedJob(data) : null;
}
