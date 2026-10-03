import type { Metadata } from "next";
import { toggleSource } from "@/lib/actions/settings";
import { requireSession } from "@/lib/auth/session";
import { formatDateTimeIST, formatDuration, relativeTime } from "@/lib/dates";
import {
  ACCESS_METHOD_LABELS,
  labelFor,
  RUN_STATUS_LABELS,
  RUN_STATUSES,
  isOneOf,
} from "@/lib/db/domain";
import {
  getSourcesWithRuns,
  type SourceRunRow,
} from "@/lib/db/queries/sources";
import { Badge, type BadgeTone } from "@/components/badge";
import { btnSecondary, card } from "@/components/ui";

export const metadata: Metadata = { title: "Sources" };

const RUN_TONES: Record<string, BadgeTone> = {
  ok: "success",
  needs_login: "warning",
  captcha: "warning",
  error: "danger",
  skipped: "neutral",
};

function RunStatus({ status }: { status: string }) {
  return (
    <Badge tone={RUN_TONES[status] ?? "neutral"}>
      {isOneOf(RUN_STATUSES, status) ? RUN_STATUS_LABELS[status] : status}
    </Badge>
  );
}

function RunSummary({ run }: { run: SourceRunRow }) {
  return (
    <div className="space-y-1 text-sm">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <RunStatus status={run.status} />
        <span>
          {run.jobs_found} found · {run.jobs_new} new
        </span>
        <span className="text-text-muted">
          <time
            dateTime={run.started_at}
            title={formatDateTimeIST(run.started_at)}
          >
            {relativeTime(run.started_at)}
          </time>{" "}
          ({formatDateTimeIST(run.started_at)})
          {run.finished_at &&
            ` · took ${formatDuration(run.started_at, run.finished_at)}`}
        </span>
      </div>
      {run.message && <p className="text-text-muted">{run.message}</p>}
    </div>
  );
}

export default async function SourcesPage() {
  await requireSession();
  const sources = await getSourcesWithRuns();

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-3 text-xl font-semibold">Sources</h1>
      <ul className="space-y-3">
        {sources.map(({ source, runs }) => {
          const [latest, ...older] = runs;
          return (
            <li key={source.id} className={`${card} space-y-3 p-4`}>
              <div className="flex flex-wrap items-start gap-3">
                <div className="min-w-0 flex-1">
                  <h2 className="font-semibold">{source.name}</h2>
                  <a
                    href={source.base_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm break-all text-accent hover:underline"
                  >
                    {source.base_url}
                  </a>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <Badge>
                      {labelFor(ACCESS_METHOD_LABELS, source.access_method)}
                    </Badge>
                    {source.requires_login && <Badge>Requires login</Badge>}
                    <Badge tone={source.enabled ? "success" : "neutral"}>
                      {source.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </div>
                </div>
                <form action={toggleSource}>
                  <input type="hidden" name="id" value={source.id} />
                  <input
                    type="hidden"
                    name="enabled"
                    value={String(!source.enabled)}
                  />
                  <button
                    type="submit"
                    role="switch"
                    aria-checked={source.enabled}
                    aria-label={`${source.name} enabled`}
                    className={btnSecondary}
                  >
                    {source.enabled ? "Disable" : "Enable"}
                  </button>
                </form>
              </div>

              <div>
                <h3 className="mb-1 text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Latest run
                </h3>
                {latest ? (
                  <RunSummary run={latest} />
                ) : (
                  <p className="text-sm text-text-muted">No runs yet</p>
                )}
              </div>

              {older.length > 0 && (
                <details>
                  <summary className="flex tap cursor-pointer items-center text-sm text-accent">
                    Previous runs ({older.length})
                  </summary>
                  <ul className="mt-2 space-y-2 border-l-2 border-border pl-3">
                    {older.map((run) => (
                      <li key={run.id}>
                        <RunSummary run={run} />
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
