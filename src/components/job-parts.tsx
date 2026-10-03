import { sourceName } from "@/lib/db/client";
import {
  APPLY_URL_KIND_LABELS,
  labelFor,
  LOCATION_BUCKET_LABELS,
  ROLE_TRACK_LABELS,
  STATUS_LABELS,
  WORK_MODE_LABELS,
} from "@/lib/db/domain";
import type { FeedJob } from "@/lib/db/jobs";
import {
  formatFit,
  formatYoe,
  isNewJob,
  salaryDisplay,
  salaryState,
} from "@/lib/format";
import { Badge } from "@/components/badge";
import { btnPrimary } from "@/components/ui";

// Pieces shared by the feed card and the job detail page.

export function JobBadges({ job }: { job: FeedJob }) {
  const bucket = labelFor(LOCATION_BUCKET_LABELS, job.locationBucket);
  const mode = labelFor(WORK_MODE_LABELS, job.workMode);
  const track = labelFor(ROLE_TRACK_LABELS, job.roleTrack);
  return (
    <div className="flex flex-wrap gap-1.5">
      {isNewJob(job.firstSeenAt) && <Badge tone="accent">NEW</Badge>}
      {job.status !== "new" && (
        <Badge tone="warning">{STATUS_LABELS[job.status]}</Badge>
      )}
      {bucket && <Badge>{bucket}</Badge>}
      {mode && <Badge>{mode}</Badge>}
      {track && <Badge>{track}</Badge>}
    </div>
  );
}

export function SalaryLine({ job }: { job: FeedJob }) {
  const yoe = formatYoe(job.minYoe, job.maxYoe);
  const state = salaryState(job);
  return (
    <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
      {state === "not_disclosed" ? (
        <Badge>Salary not disclosed</Badge>
      ) : (
        <span className="font-medium">{salaryDisplay(job)}</span>
      )}
      {job.salaryMeetsMin === true && <Badge tone="success">Meets min</Badge>}
      {state === "not_compared" && (
        <span className="text-xs text-text-muted">not compared</span>
      )}
      {yoe && (
        <>
          <span aria-hidden="true" className="text-text-muted">
            ·
          </span>
          <span>{yoe}</span>
        </>
      )}
    </p>
  );
}

export function FitLine({
  job,
  clamp = true,
}: {
  job: FeedJob;
  clamp?: boolean;
}) {
  return (
    <p className={`text-sm ${clamp ? "line-clamp-2" : ""}`}>
      <span className="font-semibold">Fit {formatFit(job.fitScore)}</span>
      {job.fitReason && (
        <span className="text-text-muted"> — {job.fitReason}</span>
      )}
    </p>
  );
}

export function SourceLinks({
  job,
  names,
}: {
  job: FeedJob;
  names: Map<string, string>;
}) {
  if (job.links.length === 0) return null;
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Source listings">
      {job.links.map((link) => (
        <li key={link.url}>
          <a
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-8 items-center rounded-md border border-border px-2 text-xs font-medium text-accent hover:bg-accent-soft"
          >
            {sourceName(names, link.source)}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

export function ApplyLink({
  job,
  className = "",
}: {
  job: FeedJob;
  className?: string;
}) {
  const kind = job.applyUrlKind
    ? APPLY_URL_KIND_LABELS[job.applyUrlKind]
    : null;
  return (
    <a
      href={job.applyUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={`${btnPrimary} flex-col gap-0 leading-tight ${className}`}
    >
      <span>
        Apply <span aria-hidden="true">↗</span>
      </span>
      {/* Where the link goes: the employer's own site or a job board. */}
      {kind && (
        <span className="text-[11px] font-normal opacity-90">
          <span className="sr-only">, </span>
          {kind}
        </span>
      )}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
