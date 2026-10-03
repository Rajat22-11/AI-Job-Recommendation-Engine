import type { Route } from "next";
import Link from "next/link";
import type { FeedJob } from "@/lib/db/jobs";
import { formatPosted, splitSkills } from "@/lib/format";
import {
  ApplyLink,
  FitLine,
  JobBadges,
  SalaryLine,
  SourceLinks,
} from "@/components/job-parts";
import { TriageActions } from "@/components/triage-actions";
import { card } from "@/components/ui";

export function JobCard({
  job,
  names,
  from,
}: {
  job: FeedJob;
  names: Map<string, string>;
  /** Current feed query, so the detail page can link back to it. */
  from: string;
}) {
  const { shown, extra } = splitSkills(job.skills);
  const href = `/jobs/${job.id}${from ? `?from=${encodeURIComponent(from)}` : ""}`;

  return (
    <article className={`${card} flex flex-col gap-2 p-4`}>
      <div>
        <h2 className="text-base leading-snug font-semibold">
          <Link
            href={href as Route}
            className="hover:text-accent hover:underline"
          >
            {job.title}
          </Link>
        </h2>
        <p className="text-sm text-text-muted">
          {job.company}
          {job.location && ` · ${job.location}`}
        </p>
      </div>

      <JobBadges job={job} />
      <SalaryLine job={job} />
      <FitLine job={job} />

      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        {shown.map((skill) => (
          <span
            key={skill}
            className="rounded-md bg-muted px-1.5 py-0.5 text-text-muted"
          >
            {skill}
          </span>
        ))}
        {extra > 0 && <span className="text-text-muted">+{extra}</span>}
        <span className="ml-auto text-text-muted">
          {formatPosted(job.postedAt, job.firstSeenAt)}
        </span>
      </div>

      <SourceLinks job={job} names={names} />

      <div className="mt-1 flex gap-2">
        <ApplyLink job={job} className="flex-[1.3]" />
        <TriageActions jobId={job.id} title={job.title} status={job.status} />
      </div>
    </article>
  );
}
