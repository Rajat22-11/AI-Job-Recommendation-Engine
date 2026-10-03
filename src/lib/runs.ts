// Pure logic for /runs and the Settings "last used by run" note.

import { addDays, formatDateTimeIST, toISTDate } from "@/lib/dates";
import type { Json } from "@/lib/db/database.types";
import { effectiveRunStatus } from "@/lib/sources";

export const RUN_HISTORY_LIMIT = 30;
export const TREND_DAYS = 14;

export interface SourceRunLike {
  id: string;
  run_id: string;
  source_id: string;
  status: string;
  jobs_found: number;
  jobs_new: number;
  message: string | null;
  started_at: string;
  finished_at: string | null;
  config_snapshot: Json | null;
}

export interface RunRowLike {
  run_id: string;
  started_at: string | null;
  finished_at: string | null;
  status: string | null;
  summary: string | null;
  config_snapshot: Json | null;
}

export type RunStatusTone = "success" | "warning" | "neutral";

export interface RunGroup<S extends SourceRunLike = SourceRunLike> {
  runId: string;
  startedAt: string | null;
  finishedAt: string | null;
  status: { label: string; tone: RunStatusTone };
  found: number;
  newJobs: number;
  summary: string | null;
  snapshot: Json | null;
  results: S[];
}

const FINE_STATUSES = ["ok", "skipped"];

function hasContent(snapshot: Json | null): boolean {
  if (snapshot === null) return false;
  if (typeof snapshot !== "object") return true;
  return Array.isArray(snapshot)
    ? snapshot.length > 0
    : Object.keys(snapshot).length > 0;
}

/**
 * One entry per run id found in either table, newest first. A `runs` row
 * supplies times, status, summary and snapshot; totals always come from the
 * per-source rows, so they match /sources.
 */
export function groupRuns<S extends SourceRunLike>(
  sourceRuns: readonly S[],
  runs: readonly RunRowLike[],
  limit = RUN_HISTORY_LIMIT,
): RunGroup<S>[] {
  const bySource = new Map<string, S[]>();
  for (const sr of sourceRuns) {
    bySource.set(sr.run_id, [...(bySource.get(sr.run_id) ?? []), sr]);
  }
  const byRun = new Map(runs.map((r) => [r.run_id, r]));
  const ids = new Set([...bySource.keys(), ...byRun.keys()]);

  const groups = [...ids].map((runId): RunGroup<S> => {
    const run = byRun.get(runId);
    const results = [...(bySource.get(runId) ?? [])].sort(
      (a, b) => Date.parse(a.started_at) - Date.parse(b.started_at),
    );

    const starts = results.map((r) => r.started_at).sort();
    const ends = results.map((r) => r.finished_at);
    const allFinished = ends.length > 0 && ends.every((e) => e !== null);
    const latestEnd = allFinished ? (ends as string[]).sort().at(-1) : null;

    let status: RunGroup["status"];
    if (run?.status) {
      status = { label: run.status, tone: "neutral" };
    } else if (
      results.every((r) =>
        FINE_STATUSES.includes(effectiveRunStatus(r.status, r.message)),
      )
    ) {
      status = { label: "OK", tone: "success" };
    } else {
      status = { label: "Needs attention", tone: "warning" };
    }

    return {
      runId,
      startedAt: run
        ? (run.started_at ?? starts[0] ?? null)
        : (starts[0] ?? null),
      finishedAt: run ? run.finished_at : (latestEnd ?? null),
      status,
      found: results.reduce((n, r) => n + r.jobs_found, 0),
      newJobs: results.reduce((n, r) => n + r.jobs_new, 0),
      summary: run?.summary ?? null,
      snapshot:
        run && hasContent(run.config_snapshot)
          ? run.config_snapshot
          : (results.find((r) => hasContent(r.config_snapshot))
              ?.config_snapshot ?? null),
      results,
    };
  });

  return groups
    .sort((a, b) => {
      if (a.startedAt === b.startedAt) return 0;
      if (a.startedAt === null) return 1;
      if (b.startedAt === null) return -1;
      return Date.parse(b.startedAt) - Date.parse(a.startedAt);
    })
    .slice(0, limit);
}

export interface TrendRow {
  /** IST calendar date, YYYY-MM-DD. */
  date: string;
  /** New jobs per source id, only for sources that ran that day. */
  perSource: Map<string, number>;
  /** Null when no run started that day. */
  total: number | null;
}

export interface Trend {
  /** Source ids with at least one run in the window. */
  sourceIds: string[];
  rows: TrendRow[];
  maxTotal: number;
}

/** New jobs per IST day and source for the last `days` days, newest first. */
export function newJobsTrend(
  sourceRuns: readonly SourceRunLike[],
  today: string,
  days = TREND_DAYS,
): Trend {
  const dates = Array.from({ length: days }, (_, i) => addDays(today, -i));
  const rows = new Map<string, TrendRow>(
    dates.map((date) => [date, { date, perSource: new Map(), total: null }]),
  );
  const sourceIds = new Set<string>();

  for (const sr of sourceRuns) {
    const row = rows.get(toISTDate(new Date(sr.started_at)));
    if (!row) continue;
    sourceIds.add(sr.source_id);
    row.perSource.set(
      sr.source_id,
      (row.perSource.get(sr.source_id) ?? 0) + sr.jobs_new,
    );
    row.total = (row.total ?? 0) + sr.jobs_new;
  }

  const list = dates.map((d) => rows.get(d) as TrendRow);
  return {
    sourceIds: [...sourceIds].sort(),
    rows: list,
    maxTotal: Math.max(0, ...list.map((r) => r.total ?? 0)),
  };
}

export interface SearchConfigLike {
  keywords: string[];
  locations: string[];
  excluded_companies: string[];
  min_salary_lpa: number;
  max_required_yoe: number;
  max_job_age_days: number;
}

/** Same labels as the Settings form. */
export const CONFIG_FIELD_LABELS: Record<keyof SearchConfigLike, string> = {
  keywords: "Keywords",
  locations: "Locations",
  excluded_companies: "Excluded companies",
  min_salary_lpa: "Minimum salary (LPA)",
  max_required_yoe: "Max required YOE",
  max_job_age_days: "Max job age (days)",
};

const CONFIG_FIELDS = Object.keys(
  CONFIG_FIELD_LABELS,
) as (keyof SearchConfigLike)[];
const LIST_FIELDS: readonly string[] = [
  "keywords",
  "locations",
  "excluded_companies",
];

function asObject(
  snapshot: Json | null,
): Record<string, Json | undefined> | null {
  return snapshot && typeof snapshot === "object" && !Array.isArray(snapshot)
    ? snapshot
    : null;
}

function display(value: Json | undefined): string {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
  if (value === null || value === undefined || value === "") return "None";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

/** Snapshot keys that are bookkeeping, not settings. */
const IGNORED_KEYS: readonly string[] = ["id"];

/**
 * The settings part of a snapshot. The trigger writes
 * `{ search_config: {...}, sources: [...] }`; a flat settings object is
 * accepted too. `rest` holds the other top-level keys.
 */
function splitSnapshot(snapshot: Json | null): {
  config: Record<string, Json | undefined>;
  rest: Record<string, Json | undefined>;
} | null {
  const obj = asObject(snapshot);
  if (!obj) return null;
  const nested = asObject(obj.search_config ?? null);
  if (!nested) return { config: obj, rest: {} };
  const rest = Object.fromEntries(
    Object.entries(obj).filter(([k]) => k !== "search_config"),
  );
  return { config: nested, rest };
}

export interface SnapshotFields {
  known: { key: string; label: string; value: string }[];
  /** Keys the app doesn't know, shown as JSON and never compared. */
  extra: Record<string, Json | undefined>;
}

export function snapshotFields(snapshot: Json | null): SnapshotFields | null {
  const parts = splitSnapshot(snapshot);
  if (!parts) return null;
  const { config, rest } = parts;
  const known = CONFIG_FIELDS.filter((k) => k in config).map((key) => ({
    key,
    label: CONFIG_FIELD_LABELS[key],
    value: display(config[key]),
  }));
  const extra = {
    ...Object.fromEntries(
      Object.entries(config).filter(
        ([k]) =>
          !(CONFIG_FIELDS as string[]).includes(k) && !IGNORED_KEYS.includes(k),
      ),
    ),
    ...rest,
  };
  if (known.length === 0 && Object.keys(extra).length === 0) return null;
  return { known, extra };
}

function listKey(value: Json | undefined): string {
  const items = Array.isArray(value) ? value : [];
  return [...new Set(items.map((v) => String(v).trim().toLowerCase()))]
    .filter(Boolean)
    .sort()
    .join("\n");
}

/**
 * Labels of known fields in the snapshot that differ from `current`, or null
 * when the snapshot has no known fields to compare.
 */
export function diffConfig(
  snapshot: Json | null,
  current: SearchConfigLike,
): string[] | null {
  const config = splitSnapshot(snapshot)?.config;
  if (!config || !CONFIG_FIELDS.some((k) => k in config)) return null;
  return CONFIG_FIELDS.filter((key) => {
    if (!(key in config)) return false;
    const value = config[key];
    if (LIST_FIELDS.includes(key)) {
      return listKey(value) !== listKey(current[key] as string[]);
    }
    return Number(value) !== Number(current[key]);
  }).map((key) => CONFIG_FIELD_LABELS[key]);
}

export interface LatestRun {
  runId: string;
  startedAt: string;
}

/** First 8 characters of a run id, as shown to the user. */
export function shortRunId(runId: string): string {
  return runId.slice(0, 8);
}

/**
 * "Last used by run 1a2b3c4d at …", and whether the settings were saved after
 * that run started (so it didn't use them).
 */
export function lastUsedNote(
  latest: LatestRun | null,
  updatedAt: string,
): { text: string; changedAfter: boolean } {
  if (!latest) return { text: "Not used by any run yet", changedAfter: false };
  return {
    text: `Last used by run ${shortRunId(latest.runId)} at ${formatDateTimeIST(latest.startedAt)}`,
    changedAfter: Date.parse(updatedAt) > Date.parse(latest.startedAt),
  };
}
