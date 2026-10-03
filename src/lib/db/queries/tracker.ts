import "server-only";
import { db } from "@/lib/db/client";
import { APP_STATUSES, isOneOf, type AppStatus } from "@/lib/db/domain";

export interface TrackerEntry {
  jobId: string;
  title: string;
  company: string;
  isActive: boolean;
  status: AppStatus;
  appliedOn: string | null;
  updatedAt: string;
}

/** applied_on newest first (undated last), then most recently updated. */
export function compareEntries(a: TrackerEntry, b: TrackerEntry): number {
  if (a.appliedOn !== b.appliedOn) {
    if (a.appliedOn === null) return 1;
    if (b.appliedOn === null) return -1;
    return a.appliedOn < b.appliedOn ? 1 : -1;
  }
  return Date.parse(b.updatedAt) - Date.parse(a.updatedAt);
}

/** Every application (active job or not), grouped by status in display order. */
export async function getTracker(): Promise<Record<AppStatus, TrackerEntry[]>> {
  // job_feed has no updated_at, so read it from applications and join by id.
  const [apps, jobs] = await Promise.all([
    db().from("applications").select("job_id, status, applied_on, updated_at"),
    db()
      .from("job_feed")
      .select("id, title, company, is_active")
      .neq("app_status", "new"),
  ]);
  if (apps.error) throw apps.error;
  if (jobs.error) throw jobs.error;

  const jobById = new Map(jobs.data.map((j) => [j.id, j]));
  const groups = Object.fromEntries(
    APP_STATUSES.map((s) => [s, []]),
  ) as unknown as Record<AppStatus, TrackerEntry[]>;

  for (const app of apps.data) {
    const job = jobById.get(app.job_id);
    if (!job || !isOneOf(APP_STATUSES, app.status)) continue;
    groups[app.status].push({
      jobId: app.job_id,
      title: job.title ?? "",
      company: job.company ?? "",
      isActive: job.is_active ?? false,
      status: app.status,
      appliedOn: app.applied_on,
      updatedAt: app.updated_at,
    });
  }
  for (const status of APP_STATUSES) groups[status].sort(compareEntries);
  return groups;
}
