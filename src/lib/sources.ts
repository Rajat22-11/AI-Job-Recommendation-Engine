import {
  isOneOf,
  QUERY_STATUSES,
  RUN_STATUSES,
  TEMPLATELESS_ACCESS_METHODS,
  type QueryStatus,
  type RunStatus,
} from "@/lib/db/domain";

export interface RunLike {
  source_id: string;
  status: string;
  started_at: string;
}

/** Latest run per source id, from runs in any order. */
export function latestRunBySource<T extends RunLike>(
  runs: readonly T[],
): Map<string, T> {
  const latest = new Map<string, T>();
  for (const run of runs) {
    const current = latest.get(run.source_id);
    if (
      !current ||
      Date.parse(run.started_at) > Date.parse(current.started_at)
    ) {
      latest.set(run.source_id, run);
    }
  }
  return latest;
}

const LOGIN_STATUSES: readonly RunStatus[] = ["needs_login", "captcha"];

export function needsLogin(status: string): boolean {
  return isOneOf(RUN_STATUSES, status) && LOGIN_STATUSES.includes(status);
}

/**
 * The status to show for a run. Before `partial` existed the trigger wrote
 * `ok` with a "PARTIAL:" message, so those rows are shown as partial too.
 */
export function effectiveRunStatus(
  status: string,
  message: string | null | undefined,
): string {
  if (status === "ok" && message && /^partial:/i.test(message)) {
    return "partial";
  }
  return status;
}

export type TemplateStateKind =
  "not_applicable" | "waiting" | "waiting_to_verify" | "verified" | "failed";

export interface TemplateState {
  kind: TemplateStateKind;
  /** Waiting, but the source is disabled so no run will pick it up. */
  disabled: boolean;
}

export interface TemplateSourceLike {
  access_method: string | null;
  search_url_template: string | null;
  template_status: string | null;
  enabled: boolean;
}

/** Where a source is in template learning. Connector, API and RSS sources never use one. */
export function templateState(source: TemplateSourceLike): TemplateState {
  const method = source.access_method;
  if (
    method &&
    (TEMPLATELESS_ACCESS_METHODS as readonly string[]).includes(method)
  ) {
    return { kind: "not_applicable", disabled: false };
  }
  if (source.template_status === "verified") {
    return { kind: "verified", disabled: false };
  }
  if (source.template_status === "failed") {
    return { kind: "failed", disabled: false };
  }
  // `unverified`, or empty on rows written before the column existed.
  return {
    kind: source.search_url_template ? "waiting_to_verify" : "waiting",
    disabled: !source.enabled,
  };
}

/** One-line summary of a template state, e.g. for a collapsed row. */
export function templateStateSummary(state: TemplateState): string {
  if (state.disabled) return "Template: won't be learned while disabled";
  switch (state.kind) {
    case "not_applicable":
      return "Template: not applicable";
    case "waiting":
      return "Template: waiting for first run";
    case "waiting_to_verify":
      return "Template: will be verified on the next run";
    case "verified":
      return "Template: verified";
    case "failed":
      return "Template: couldn't be learned";
  }
}

/** Re-learning is offered once the trigger has reached a verdict. */
export function canRelearn(state: TemplateState): boolean {
  return state.kind === "verified" || state.kind === "failed";
}

export const EMPTY_RUN_WARNING_THRESHOLD = 3;

export function emptyRunWarning(consecutiveEmptyRuns: number): string | null {
  return consecutiveEmptyRuns >= EMPTY_RUN_WARNING_THRESHOLD
    ? `No jobs found in the last ${consecutiveEmptyRuns} runs`
    : null;
}

export interface QueryRowLike {
  status: string;
}

const UNFINISHED_QUERY_STATUSES: readonly QueryStatus[] = [
  "pending",
  "rate_limited",
  "failed",
];

/** How much of a run's planned queries finished, and which will be resumed. */
export function queryCoverage<T extends QueryRowLike>(
  rows: readonly T[],
): { done: number; total: number; unfinished: T[] } {
  return {
    done: rows.filter((r) => r.status === "done").length,
    total: rows.length,
    unfinished: rows.filter(
      (r) =>
        isOneOf(QUERY_STATUSES, r.status) &&
        UNFINISHED_QUERY_STATUSES.includes(r.status),
    ),
  };
}

/** Enabled sources whose latest run needs the user to log in. */
export function loginAlerts(
  sources: readonly { id: string; name: string; enabled: boolean }[],
  runs: readonly RunLike[],
): { id: string; name: string }[] {
  const latest = latestRunBySource(runs);
  return sources
    .filter((s) => s.enabled)
    .filter((s) => {
      const run = latest.get(s.id);
      return run !== undefined && needsLogin(run.status);
    })
    .map(({ id, name }) => ({ id, name }));
}
