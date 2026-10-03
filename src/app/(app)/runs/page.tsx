import type { Metadata } from "next";
import { requireSession } from "@/lib/auth/session";
import {
  formatDate,
  formatDateTimeIST,
  formatDuration,
  relativeTime,
  todayIST,
} from "@/lib/dates";
import { db, getSourceNames, sourceName } from "@/lib/db/client";
import { getRunHistory, type SourceRunHistoryRow } from "@/lib/db/queries/runs";
import {
  diffConfig,
  groupRuns,
  newJobsTrend,
  shortRunId,
  snapshotFields,
  type RunGroup,
  type SearchConfigLike,
  type Trend,
} from "@/lib/runs";
import { Badge } from "@/components/badge";
import { RunStatusBadge } from "@/components/run-status-badge";
import { card } from "@/components/ui";

export const metadata: Metadata = { title: "Runs" };

const summaryLink = "flex tap cursor-pointer items-center text-sm text-accent";

async function getSearchConfig(): Promise<SearchConfigLike> {
  const { data, error } = await db()
    .from("search_config")
    .select("*")
    .eq("id", 1)
    .single();
  if (error) throw error;
  return data;
}

function SourceResults({
  group,
  names,
}: {
  group: RunGroup<SourceRunHistoryRow>;
  names: Map<string, string>;
}) {
  if (group.results.length === 0) return null;
  return (
    <details>
      <summary className={summaryLink}>
        Sources ({group.results.length})
      </summary>
      <ul className="mt-2 space-y-2 border-l-2 border-border pl-3 text-sm">
        {group.results.map((r) => (
          <li key={r.id}>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-medium">
                {sourceName(names, r.source_id)}
              </span>
              <RunStatusBadge status={r.status} message={r.message} />
              <span>
                {r.jobs_found} found · {r.jobs_new} new
              </span>
            </div>
            {r.message && (
              <p className="break-words text-text-muted">{r.message}</p>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}

function ConfigSnapshot({
  group,
  current,
}: {
  group: RunGroup;
  current: SearchConfigLike;
}) {
  const fields = snapshotFields(group.snapshot);
  if (!fields) {
    return (
      <p className="text-sm text-text-muted">No config snapshot recorded</p>
    );
  }
  const differs = diffConfig(group.snapshot, current);
  const extra = Object.keys(fields.extra).length > 0;
  return (
    <details>
      <summary className={summaryLink}>
        Config snapshot ·{" "}
        {differs === null
          ? "No settings to compare"
          : differs.length === 0
            ? "Same as current settings"
            : `Differs from current settings: ${differs.join(", ")}`}
      </summary>
      <dl className="mt-2 grid gap-x-3 gap-y-1 border-l-2 border-border pl-3 text-sm empty:hidden sm:grid-cols-[auto_1fr]">
        {fields.known.map((f) => (
          <div key={f.key} className="contents">
            <dt className="text-text-muted">{f.label}</dt>
            <dd className="break-words">{f.value}</dd>
          </div>
        ))}
      </dl>
      {extra && (
        <pre className="mt-2 overflow-x-auto rounded-md bg-muted p-2 text-xs">
          {JSON.stringify(fields.extra, null, 2)}
        </pre>
      )}
    </details>
  );
}

function RunItem({
  group,
  names,
  current,
}: {
  group: RunGroup<SourceRunHistoryRow>;
  names: Map<string, string>;
  current: SearchConfigLike;
}) {
  return (
    <li
      id={`run-${group.runId}`}
      className={`${card} scroll-mt-4 space-y-2 p-4`}
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <h3 className="font-semibold">
          Run <code className="text-sm">{shortRunId(group.runId)}</code>
        </h3>
        <Badge tone={group.status.tone}>{group.status.label}</Badge>
        <span className="text-sm">
          {group.found} found · {group.newJobs} new
        </span>
      </div>
      {group.startedAt && (
        <p className="text-sm text-text-muted">
          <time
            dateTime={group.startedAt}
            title={formatDateTimeIST(group.startedAt)}
          >
            {relativeTime(group.startedAt)}
          </time>{" "}
          ({formatDateTimeIST(group.startedAt)})
          {group.finishedAt &&
            ` · took ${formatDuration(group.startedAt, group.finishedAt)}`}
        </p>
      )}
      {group.summary && <p className="text-sm break-words">{group.summary}</p>}
      <SourceResults group={group} names={names} />
      <ConfigSnapshot group={group} current={current} />
    </li>
  );
}

function TrendTable({
  trend,
  names,
}: {
  trend: Trend;
  names: Map<string, string>;
}) {
  const columns = trend.sourceIds
    .map((id) => ({ id, name: sourceName(names, id) }))
    .sort((a, b) => a.name.localeCompare(b.name));
  const cell = "px-2 py-1.5 text-right tabular-nums";
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-sm">
        <caption className="sr-only">
          New jobs per day and source, last 14 days
        </caption>
        <thead className="text-xs text-text-muted">
          <tr className="border-b border-border">
            <th scope="col" className="px-2 py-1.5 text-left font-medium">
              Day
            </th>
            {columns.map((c) => (
              <th
                key={c.id}
                scope="col"
                className={`${cell} font-medium whitespace-nowrap`}
              >
                {c.name}
              </th>
            ))}
            <th scope="col" className="px-2 py-1.5 text-left font-medium">
              Total
            </th>
          </tr>
        </thead>
        <tbody>
          {trend.rows.map((row) => (
            <tr key={row.date} className="border-b border-border last:border-0">
              <th
                scope="row"
                className="px-2 py-1.5 text-left font-normal whitespace-nowrap"
              >
                {formatDate(row.date).replace(/ \d{4}$/, "")}
              </th>
              {columns.map((c) => (
                <td key={c.id} className={cell}>
                  {row.perSource.get(c.id) ?? "—"}
                </td>
              ))}
              <td className="px-2 py-1.5">
                {row.total === null ? (
                  <span className="text-text-muted">—</span>
                ) : (
                  <div className="flex min-w-24 items-center gap-2">
                    <span className="w-6 text-right tabular-nums">
                      {row.total}
                    </span>
                    <div className="h-2 flex-1 rounded-full bg-muted">
                      <div
                        className="h-2 rounded-full bg-accent"
                        style={{
                          width: `${trend.maxTotal ? (row.total / trend.maxTotal) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function RunsPage() {
  await requireSession();
  const [{ sourceRuns, runs }, names, current] = await Promise.all([
    getRunHistory(),
    getSourceNames(),
    getSearchConfig(),
  ]);
  const groups = groupRuns(sourceRuns, runs);
  const trend = newJobsTrend(sourceRuns, todayIST());

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-xl font-semibold">Runs</h1>

      <section aria-labelledby="trend-heading" className="space-y-2">
        <h2 id="trend-heading" className="text-lg font-semibold">
          New jobs, last 14 days
        </h2>
        <TrendTable trend={trend} names={names} />
      </section>

      <section aria-labelledby="runs-heading" className="space-y-2">
        <h2 id="runs-heading" className="text-lg font-semibold">
          Recent runs
        </h2>
        {groups.length === 0 ? (
          <p className="text-sm text-text-muted">No runs yet</p>
        ) : (
          <ul className="space-y-3">
            {groups.map((group) => (
              <RunItem
                key={group.runId}
                group={group}
                names={names}
                current={current}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
