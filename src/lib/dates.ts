// All calendar dates are India Standard Time, whatever the server's zone.

export const APP_TIME_ZONE = "Asia/Kolkata";

const HOUR_MS = 60 * 60 * 1000;
const DAY_MS = 24 * HOUR_MS;

const isoDateFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: APP_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** Calendar date in IST as YYYY-MM-DD. */
export function toISTDate(at: Date): string {
  return isoDateFormat.format(at);
}

export function todayIST(now: Date = new Date()): string {
  return toISTDate(now);
}

/** Shift a YYYY-MM-DD date by whole days. */
export function addDays(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Whole calendar days from `date` (YYYY-MM-DD) to today in IST. */
export function daysSinceDate(date: string, now: Date = new Date()): number {
  const from = Date.parse(`${date}T00:00:00Z`);
  const to = Date.parse(`${todayIST(now)}T00:00:00Z`);
  return Math.round((to - from) / DAY_MS);
}

export function isWithin24h(
  timestamp: string,
  now: Date = new Date(),
): boolean {
  const age = now.getTime() - Date.parse(timestamp);
  return age >= 0 && age < DAY_MS;
}

/** "Today", "1d ago", "3d ago" for a date-only value. */
export function relativeDate(date: string, now: Date = new Date()): string {
  const days = daysSinceDate(date, now);
  if (days <= 0) return "Today";
  return `${days}d ago`;
}

/** "just now", "5m ago", "3h ago", "2d ago" for a timestamp. */
export function relativeTime(
  timestamp: string,
  now: Date = new Date(),
): string {
  const age = now.getTime() - Date.parse(timestamp);
  if (age < 60 * 1000) return "just now";
  if (age < HOUR_MS) return `${Math.floor(age / 60000)}m ago`;
  if (age < DAY_MS) return `${Math.floor(age / HOUR_MS)}h ago`;
  return `${Math.floor(age / DAY_MS)}d ago`;
}

const dateFormat = new Intl.DateTimeFormat("en-IN", {
  timeZone: "UTC",
  day: "numeric",
  month: "short",
  year: "numeric",
});

/** "3 Oct 2026" for a YYYY-MM-DD value (no zone shift). */
export function formatDate(date: string): string {
  return dateFormat.format(new Date(`${date}T00:00:00Z`));
}

const dateTimeFormat = new Intl.DateTimeFormat("en-IN", {
  timeZone: APP_TIME_ZONE,
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/** "3 Oct 2026, 2:05 pm" in IST for a timestamp. */
export function formatDateTimeIST(timestamp: string): string {
  return dateTimeFormat.format(new Date(timestamp));
}

/** "4m 12s" between two timestamps. */
export function formatDuration(start: string, end: string): string {
  const seconds = Math.max(
    0,
    Math.round((Date.parse(end) - Date.parse(start)) / 1000),
  );
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}
