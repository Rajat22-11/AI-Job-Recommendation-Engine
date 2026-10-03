import {
  APPLY_URL_KINDS,
  FEED_STATUSES,
  isOneOf,
  type ApplyUrlKind,
  type FeedStatus,
} from "@/lib/db/domain";
import type { Database, Json } from "./database.types";

type FeedRow = Database["public"]["Views"]["job_feed"]["Row"];

export interface JobLink {
  source: string;
  url: string;
}

/** A job_feed row with the columns the view always fills made non-null. */
export interface FeedJob {
  id: string;
  title: string;
  company: string;
  location: string | null;
  locationBucket: string | null;
  workMode: string | null;
  employmentType: string | null;
  roleTrack: string | null;
  minYoe: number | null;
  maxYoe: number | null;
  salaryText: string | null;
  salaryMinLpa: number | null;
  salaryMaxLpa: number | null;
  salaryMeetsMin: boolean | null;
  skills: string[];
  summary: string | null;
  applyUrl: string;
  applyUrlKind: ApplyUrlKind | null;
  postedAt: string | null;
  fitScore: number | null;
  fitReason: string | null;
  isActive: boolean;
  firstSeenAt: string;
  lastSeenAt: string;
  status: FeedStatus;
  appliedOn: string | null;
  notes: string | null;
  resumeVersion: string | null;
  referralContact: string | null;
  links: JobLink[];
}

function parseLinks(value: Json | null): JobLink[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      const { source, url } = item;
      if (typeof source === "string" && typeof url === "string")
        return [{ source, url }];
    }
    return [];
  });
}

export function toFeedJob(row: FeedRow): FeedJob {
  return {
    id: row.id ?? "",
    title: row.title ?? "",
    company: row.company ?? "",
    location: row.location,
    locationBucket: row.location_bucket,
    workMode: row.work_mode,
    employmentType: row.employment_type,
    roleTrack: row.role_track,
    minYoe: row.min_yoe,
    maxYoe: row.max_yoe,
    salaryText: row.salary_text,
    salaryMinLpa: row.salary_min_lpa,
    salaryMaxLpa: row.salary_max_lpa,
    salaryMeetsMin: row.salary_meets_min,
    skills: row.skills ?? [],
    summary: row.summary,
    applyUrl: row.apply_url ?? "",
    applyUrlKind: isOneOf(APPLY_URL_KINDS, row.apply_url_kind)
      ? row.apply_url_kind
      : null,
    postedAt: row.posted_at,
    fitScore: row.fit_score,
    fitReason: row.fit_reason,
    isActive: row.is_active ?? false,
    firstSeenAt: row.first_seen_at ?? new Date(0).toISOString(),
    lastSeenAt: row.last_seen_at ?? new Date(0).toISOString(),
    status: isOneOf(FEED_STATUSES, row.app_status) ? row.app_status : "new",
    appliedOn: row.applied_on,
    notes: row.app_notes,
    resumeVersion: row.resume_version,
    referralContact: row.referral_contact,
    links: parseLinks(row.links),
  };
}

export const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
