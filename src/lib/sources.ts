import { isOneOf, RUN_STATUSES, type RunStatus } from "@/lib/db/domain";

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
