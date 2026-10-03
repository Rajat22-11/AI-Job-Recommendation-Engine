import { addDays, todayIST } from "@/lib/dates";

// PostgREST `or=(...)` filter strings for the feed. Kept pure for testing.

const MIN_SEARCH_LENGTH = 2;

/** Strip characters that carry meaning in PostgREST filters or LIKE patterns. */
export function sanitizeSearch(q: string): string | null {
  const cleaned = q
    .replace(/[*%_\\"(),:{}[\]]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cleaned.length >= MIN_SEARCH_LENGTH ? cleaned : null;
}

/** As typed, lowercase, uppercase and capitalized; duplicates removed. */
export function caseVariants(term: string): string[] {
  const lower = term.toLowerCase();
  const capitalized = lower.charAt(0).toUpperCase() + lower.slice(1);
  return [...new Set([term, lower, term.toUpperCase(), capitalized])];
}

/** Title or company contains the term (any case), or a skill equals a case variant. */
export function searchFilter(term: string): string {
  const parts = [`title.ilike."*${term}*"`, `company.ilike."*${term}*"`];
  for (const variant of caseVariants(term)) {
    parts.push(`skills.cs.{"${variant}"}`);
  }
  return parts.join(",");
}

/** At least one `links` entry from any of the given sources. */
export function sourceFilter(sourceIds: readonly string[]): string {
  return sourceIds.map((id) => `links.cs.[{"source":"${id}"}]`).join(",");
}

/**
 * Posted within `days` days (IST). Jobs without a posted date are judged by
 * when the scraper first saw them.
 */
export function postedFilter(days: number, now: Date = new Date()): string {
  const since = addDays(todayIST(now), -days);
  const seenSince = new Date(
    now.getTime() - days * 24 * 60 * 60 * 1000,
  ).toISOString();
  return `posted_at.gte.${since},and(posted_at.is.null,first_seen_at.gte.${seenSince})`;
}
