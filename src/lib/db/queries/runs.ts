import "server-only";
import { db } from "@/lib/db/client";
import type { LatestRun } from "@/lib/runs";

const DAY_MS = 24 * 60 * 60 * 1000;
const HISTORY_DAYS = 45;
const MAX_SOURCE_RUNS = 1000;

/** Recent per-source results and run rows; grouped by groupRuns(). */
export async function getRunHistory() {
  const since = new Date(Date.now() - HISTORY_DAYS * DAY_MS).toISOString();
  const [sourceRuns, runs] = await Promise.all([
    db()
      .from("source_runs")
      .select("*")
      .gte("started_at", since)
      .order("started_at", { ascending: false })
      .limit(MAX_SOURCE_RUNS),
    db()
      .from("runs")
      .select("*")
      .order("started_at", { ascending: false, nullsFirst: false })
      .limit(30),
  ]);
  if (sourceRuns.error) throw sourceRuns.error;
  if (runs.error) throw runs.error;
  return { sourceRuns: sourceRuns.data, runs: runs.data };
}

export type SourceRunHistoryRow = Awaited<
  ReturnType<typeof getRunHistory>
>["sourceRuns"][number];

/** The most recently started run, from either table. */
export async function getLatestRun(): Promise<LatestRun | null> {
  const [fromRuns, fromSources] = await Promise.all([
    db()
      .from("runs")
      .select("run_id, started_at")
      .not("started_at", "is", null)
      .order("started_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
    db()
      .from("source_runs")
      .select("run_id, started_at")
      .order("started_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
  ]);
  if (fromRuns.error) throw fromRuns.error;
  if (fromSources.error) throw fromSources.error;

  const candidates = [fromRuns.data, fromSources.data].flatMap((row) =>
    row?.started_at ? [{ runId: row.run_id, startedAt: row.started_at }] : [],
  );
  candidates.sort((a, b) => Date.parse(b.startedAt) - Date.parse(a.startedAt));
  return candidates[0] ?? null;
}
