import "server-only";
import { db } from "@/lib/db/client";
import { loginAlerts } from "@/lib/sources";

export async function getSources() {
  const { data, error } = await db().from("sources").select("*").order("name");
  if (error) throw error;
  return data;
}

export type SourceRow = Awaited<ReturnType<typeof getSources>>[number];

/** Most recent runs for one source (uses source_runs_recent_idx). */
async function recentRuns(sourceId: string, limit: number) {
  const { data, error } = await db()
    .from("source_runs")
    .select("*")
    .eq("source_id", sourceId)
    .order("started_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data;
}

export type SourceRunRow = Awaited<ReturnType<typeof recentRuns>>[number];

/** Search queries a source ran in one run (uses source_run_queries_source_run_idx). */
async function runQueries(sourceId: string, runId: string) {
  const { data, error } = await db()
    .from("source_run_queries")
    .select("*")
    .eq("source_id", sourceId)
    .eq("run_id", runId)
    .order("created_at");
  if (error) throw error;
  return data;
}

export type RunQueryRow = Awaited<ReturnType<typeof runQueries>>[number];

/** Each source with its 5 most recent runs, newest first, and the latest run's queries. */
export async function getSourcesWithRuns() {
  const sources = await getSources();
  return Promise.all(
    sources.map(async (source) => {
      const runs = await recentRuns(source.id, 5);
      const latest = runs[0];
      const queries = latest ? await runQueries(source.id, latest.run_id) : [];
      return { source, runs, queries };
    }),
  );
}

/** Enabled sources whose latest run is needs_login or captcha. */
export async function getLoginAlerts() {
  const { data: sources, error } = await db()
    .from("sources")
    .select("id, name, enabled")
    .eq("enabled", true)
    .order("name");
  if (error) throw error;
  const latest = await Promise.all(sources.map((s) => recentRuns(s.id, 1)));
  return loginAlerts(sources, latest.flat());
}
