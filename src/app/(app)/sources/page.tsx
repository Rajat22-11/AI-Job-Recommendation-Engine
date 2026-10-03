import type { Metadata } from "next";
import type { ReactNode } from "react";
import { relearnTemplate, toggleSource } from "@/lib/actions/settings";
import { requireSession } from "@/lib/auth/session";
import { formatDateTimeIST, formatDuration, relativeTime } from "@/lib/dates";
import {
  ACCESS_METHOD_LABELS,
  labelFor,
  QUERY_STATUS_LABELS,
  TEMPLATE_ORIGIN_LABELS,
} from "@/lib/db/domain";
import {
  getSourcesWithRuns,
  type RunQueryRow,
  type SourceRow,
  type SourceRunRow,
} from "@/lib/db/queries/sources";
import {
  canRelearn,
  emptyRunWarning,
  queryCoverage,
  templateState,
} from "@/lib/sources";
import { Badge } from "@/components/badge";
import { RunStatusBadge } from "@/components/run-status-badge";
import { btnSecondary, card } from "@/components/ui";

export const metadata: Metadata = { title: "Sources" };

const sectionHeading =
  "mb-1 text-xs font-semibold tracking-wide text-text-muted uppercase";

function Time({ at }: { at: string }) {
  return (
    <time dateTime={at} title={formatDateTimeIST(at)}>
      {relativeTime(at)}
    </time>
  );
}

function RunSummary({ run }: { run: SourceRunRow }) {
  return (
    <div className="space-y-1 text-sm">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <RunStatusBadge status={run.status} message={run.message} />
        <span>
          {run.jobs_found} found · {run.jobs_new} new
        </span>
        <span className="text-text-muted">
          <Time at={run.started_at} /> ({formatDateTimeIST(run.started_at)})
          {run.finished_at &&
            ` · took ${formatDuration(run.started_at, run.finished_at)}`}
        </span>
      </div>
      {run.message && (
        <p className="break-words text-text-muted">{run.message}</p>
      )}
    </div>
  );
}

function TemplateCode({ template }: { template: string }) {
  return (
    <code className="block rounded-md bg-muted px-2 py-1 text-xs break-all text-text">
      {template}
    </code>
  );
}

function TemplateBlock({ source }: { source: SourceRow }) {
  const state = templateState(source);
  const template = source.search_url_template;

  let body: ReactNode;
  if (state.kind === "not_applicable") {
    body = (
      <p className="text-text-muted">
        Not applicable. This access method doesn&apos;t use a search URL
        template.
      </p>
    );
  } else if (state.disabled) {
    body = (
      <p className="text-text-muted">
        Disabled. The template won&apos;t be learned until the source is
        enabled.
      </p>
    );
  } else if (state.kind === "waiting") {
    body = (
      <p>Waiting for first run. The template will be learned automatically.</p>
    );
  } else if (state.kind === "waiting_to_verify") {
    body = (
      <>
        <p>Will be verified on the next run.</p>
        {template && <TemplateCode template={template} />}
      </>
    );
  } else if (state.kind === "verified") {
    const origin = labelFor(TEMPLATE_ORIGIN_LABELS, source.template_origin);
    body = (
      <>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Badge tone="success">Verified</Badge>
          {origin && <Badge>{origin}</Badge>}
          {source.template_verified_at && (
            <span className="text-text-muted">
              Verified <Time at={source.template_verified_at} />
            </span>
          )}
        </div>
        {template && <TemplateCode template={template} />}
      </>
    );
  } else {
    body = (
      <>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="danger">Failed</Badge>
          <span>Couldn&apos;t learn the template</span>
        </div>
        <p className="break-words text-text-muted">
          {source.template_notes || "No reason recorded"}
        </p>
      </>
    );
  }

  return (
    <div>
      <h3 className={sectionHeading}>Search URL template</h3>
      <div className="space-y-2 text-sm">
        {body}
        {canRelearn(state) && (
          <form action={relearnTemplate}>
            <input type="hidden" name="id" value={source.id} />
            <button type="submit" className={btnSecondary}>
              Re-learn template
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function QueryCoverage({ queries }: { queries: RunQueryRow[] }) {
  if (queries.length === 0) return null;
  const { done, total, unfinished } = queryCoverage(queries);
  return (
    <div className="space-y-1 text-sm">
      <p>
        {done} of {total} queries done
      </p>
      {unfinished.length > 0 && (
        <details>
          <summary className="flex tap cursor-pointer items-center text-accent">
            Will resume on the next run ({unfinished.length})
          </summary>
          <ul className="mt-2 space-y-2 border-l-2 border-border pl-3">
            {unfinished.map((q) => (
              <li key={q.id} className="break-words">
                <span className="font-medium">
                  {[q.keyword, q.location].filter(Boolean).join(" · ") ||
                    "Query"}
                </span>
                {q.page !== null && (
                  <span className="text-text-muted"> · page {q.page}</span>
                )}{" "}
                <Badge tone={q.status === "failed" ? "danger" : "warning"}>
                  {labelFor(QUERY_STATUS_LABELS, q.status)}
                </Badge>
                {q.error && <p className="text-text-muted">{q.error}</p>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function ScrapeHints({ hints }: { hints: SourceRow["scrape_hints"] }) {
  const empty =
    hints === null ||
    (typeof hints === "object" && Object.keys(hints).length === 0);
  if (empty) return null;
  return (
    <details className="text-sm">
      <summary className="flex tap cursor-pointer items-center text-accent">
        Scrape hints
      </summary>
      <pre className="mt-2 overflow-x-auto rounded-md bg-muted p-2 text-xs">
        {JSON.stringify(hints, null, 2)}
      </pre>
    </details>
  );
}

export default async function SourcesPage() {
  await requireSession();
  const sources = await getSourcesWithRuns();

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-3 text-xl font-semibold">Sources</h1>
      <ul className="space-y-3">
        {sources.map(({ source, runs, queries }) => {
          const [latest, ...older] = runs;
          const method = labelFor(ACCESS_METHOD_LABELS, source.access_method);
          const warning = emptyRunWarning(source.consecutive_empty_runs);
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
                    {method && <Badge>{method}</Badge>}
                    {source.requires_login && <Badge>Requires login</Badge>}
                    <Badge tone={source.enabled ? "success" : "neutral"}>
                      {source.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                    {warning && <Badge tone="warning">{warning}</Badge>}
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

              <TemplateBlock source={source} />
              <ScrapeHints hints={source.scrape_hints} />

              <div>
                <h3 className={sectionHeading}>Latest run</h3>
                <p className="mb-1 text-sm text-text-muted">
                  Last success{" "}
                  {source.last_success_at ? (
                    <>
                      <Time at={source.last_success_at} /> (
                      {formatDateTimeIST(source.last_success_at)})
                    </>
                  ) : (
                    "Never"
                  )}
                </p>
                {latest ? (
                  <div className="space-y-2">
                    <RunSummary run={latest} />
                    <QueryCoverage queries={queries} />
                  </div>
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
