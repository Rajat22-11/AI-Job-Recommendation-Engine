import { isWithin24h, relativeDate, relativeTime } from "@/lib/dates";

function num(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1).replace(/\.0$/, "");
}

/** "1–3 yrs", "3+ yrs", "Up to 3 yrs", or null when not stated. */
export function formatYoe(
  min: number | null,
  max: number | null,
): string | null {
  if (min !== null && max !== null) {
    return min === max ? `${num(min)} yrs` : `${num(min)}–${num(max)} yrs`;
  }
  if (min !== null) return `${num(min)}+ yrs`;
  if (max !== null) return `Up to ${num(max)} yrs`;
  return null;
}

export function formatSalary(salaryText: string | null): string {
  return salaryText?.trim() || "Salary not disclosed";
}

/** "₹12–18 LPA" from the numeric range, or null. */
export function formatSalaryRange(
  min: number | null,
  max: number | null,
): string | null {
  if (min !== null && max !== null && min !== max)
    return `₹${num(min)}–${num(max)} LPA`;
  const one = min ?? max;
  return one !== null ? `₹${num(one)} LPA` : null;
}

export function formatFit(score: number | null): string {
  return score === null ? "Not scored" : `${score}/5`;
}

/** Posted date, falling back to when the scraper first saw the job. */
export function formatPosted(
  postedAt: string | null,
  firstSeenAt: string,
  now: Date = new Date(),
): string {
  if (postedAt) return relativeDate(postedAt, now);
  return `Seen ${relativeTime(firstSeenAt, now)}`;
}

export function isNewJob(firstSeenAt: string, now: Date = new Date()): boolean {
  return isWithin24h(firstSeenAt, now);
}

export function splitSkills(skills: readonly string[], max = 6) {
  return {
    shown: skills.slice(0, max),
    extra: Math.max(0, skills.length - max),
  };
}
