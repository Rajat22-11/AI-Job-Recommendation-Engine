// Value sets mirroring the database CHECK constraints. Generated types only say
// `string` for these columns, so queries narrow to these unions.

export const APP_STATUSES = [
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
  "skipped",
] as const;
export type AppStatus = (typeof APP_STATUSES)[number];

/** `new` is derived by the job_feed view when no application row exists. */
export const FEED_STATUSES = ["new", ...APP_STATUSES] as const;
export type FeedStatus = (typeof FEED_STATUSES)[number];

export const STATUS_LABELS: Record<FeedStatus, string> = {
  new: "New",
  saved: "Saved",
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  skipped: "Skipped",
};

export const ROLE_TRACKS = [
  "java_backend",
  "ml_ai",
  "data",
  "full_stack",
  "other",
] as const;
export type RoleTrack = (typeof ROLE_TRACKS)[number];

export const ROLE_TRACK_LABELS: Record<RoleTrack, string> = {
  java_backend: "Java backend",
  ml_ai: "ML / AI",
  data: "Data",
  full_stack: "Full stack",
  other: "Other",
};

export const LOCATION_BUCKETS = [
  "pune",
  "mumbai",
  "gujarat",
  "remote_india",
  "remote_international",
  "other",
] as const;
export type LocationBucket = (typeof LOCATION_BUCKETS)[number];

export const LOCATION_BUCKET_LABELS: Record<LocationBucket, string> = {
  pune: "Pune",
  mumbai: "Mumbai",
  gujarat: "Gujarat",
  remote_india: "Remote (India)",
  remote_international: "Remote (Intl)",
  other: "Other",
};

export const WORK_MODES = ["onsite", "hybrid", "remote"] as const;
export type WorkMode = (typeof WORK_MODES)[number];

export const WORK_MODE_LABELS: Record<WorkMode, string> = {
  onsite: "Onsite",
  hybrid: "Hybrid",
  remote: "Remote",
};

export const ACCESS_METHODS = [
  "auto",
  "connector",
  "public_scrape",
  "browser_session",
  "api",
  "rss",
] as const;
export type AccessMethod = (typeof ACCESS_METHODS)[number];

export const ACCESS_METHOD_LABELS: Record<AccessMethod, string> = {
  auto: "Auto-detect",
  connector: "Connector",
  public_scrape: "Public scrape",
  browser_session: "Browser session",
  api: "API",
  rss: "RSS",
};

/** Access methods that never use a search URL template. */
export const TEMPLATELESS_ACCESS_METHODS: readonly AccessMethod[] = [
  "connector",
  "api",
  "rss",
];

export const RUN_STATUSES = [
  "ok",
  "partial",
  "needs_login",
  "captcha",
  "error",
  "skipped",
] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

export const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  ok: "OK",
  partial: "Partial",
  needs_login: "Needs login",
  captcha: "Captcha",
  error: "Error",
  skipped: "Skipped",
};

export const TEMPLATE_STATUSES = ["unverified", "verified", "failed"] as const;
export type TemplateStatus = (typeof TEMPLATE_STATUSES)[number];

export const TEMPLATE_STATUS_LABELS: Record<TemplateStatus, string> = {
  unverified: "Unverified",
  verified: "Verified",
  failed: "Failed",
};

export const TEMPLATE_ORIGINS = ["manual", "auto"] as const;
export type TemplateOrigin = (typeof TEMPLATE_ORIGINS)[number];

export const TEMPLATE_ORIGIN_LABELS: Record<TemplateOrigin, string> = {
  manual: "Manual",
  auto: "Learned",
};

export const QUERY_STATUSES = [
  "done",
  "pending",
  "rate_limited",
  "failed",
  "skipped",
] as const;
export type QueryStatus = (typeof QUERY_STATUSES)[number];

export const QUERY_STATUS_LABELS: Record<QueryStatus, string> = {
  done: "Done",
  pending: "Pending",
  rate_limited: "Rate limited",
  failed: "Failed",
  skipped: "Skipped",
};

export const APPLY_URL_KINDS = ["employer", "board"] as const;
export type ApplyUrlKind = (typeof APPLY_URL_KINDS)[number];

export const APPLY_URL_KIND_LABELS: Record<ApplyUrlKind, string> = {
  employer: "Employer site",
  board: "Job board",
};

export function isOneOf<T extends string>(
  values: readonly T[],
  value: unknown,
): value is T {
  return (
    typeof value === "string" && (values as readonly string[]).includes(value)
  );
}

/** Label for a constrained value, falling back to the raw value. */
export function labelFor<T extends string>(
  labels: Record<T, string>,
  value: string | null | undefined,
): string | null {
  if (!value) return null;
  return (labels as Record<string, string>)[value] ?? value;
}
