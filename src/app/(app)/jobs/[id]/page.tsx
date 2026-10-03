import type { Metadata, Route } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cache } from "react";
import { requireSession } from "@/lib/auth/session";
import {
  formatDate,
  formatDateTimeIST,
  relativeTime,
  todayIST,
  toISTDate,
} from "@/lib/dates";
import { getSourceNames } from "@/lib/db/client";
import { getJob } from "@/lib/db/queries/feed";
import { safeFeedQuery } from "@/lib/feed/params";
import { formatPosted, formatSalaryRange } from "@/lib/format";
import {
  ApplyLink,
  FitLine,
  JobBadges,
  SalaryLine,
  SourceLinks,
} from "@/components/job-parts";
import { TriageActions } from "@/components/triage-actions";
import { card } from "@/components/ui";
import { ApplicationForm } from "./application-form";

const loadJob = cache(getJob);

export async function generateMetadata({
  params,
}: PageProps<"/jobs/[id]">): Promise<Metadata> {
  const job = await loadJob((await params).id);
  return { title: job ? `${job.title} at ${job.company}` : "Job not found" };
}

export default async function JobPage({
  params,
  searchParams,
}: PageProps<"/jobs/[id]">) {
  await requireSession();
  const [{ id }, { from }] = await Promise.all([params, searchParams]);
  const [job, names] = await Promise.all([loadJob(id), getSourceNames()]);
  if (!job) notFound();

  const backHref = `/${safeFeedQuery(from)}` as Route;
  const range = formatSalaryRange(job.salaryMinLpa, job.salaryMaxLpa);

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Link
        href={backHref}
        className="inline-flex tap items-center text-sm text-accent"
      >
        ← Back to feed
      </Link>

      <article className={`${card} space-y-3 p-4 sm:p-6`}>
        {!job.isActive && (
          <p
            role="note"
            className="rounded-lg bg-warning-soft p-3 text-sm text-warning"
          >
            <strong>No longer active.</strong> Last seen{" "}
            {formatDate(toISTDate(new Date(job.lastSeenAt)))}.
          </p>
        )}
        <div>
          <h1 className="text-xl leading-snug font-semibold">{job.title}</h1>
          <p className="text-text-muted">
            {job.company}
            {job.location && ` · ${job.location}`}
          </p>
        </div>

        <JobBadges job={job} />
        <SalaryLine job={job} />
        {range && <p className="text-sm text-text-muted">Range: {range}</p>}
        <FitLine job={job} clamp={false} />

        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-text-muted">Posted</dt>
          <dd>
            {job.postedAt
              ? `${formatDate(job.postedAt)} (${formatPosted(job.postedAt, job.firstSeenAt)})`
              : "Not stated"}
          </dd>
          {job.employmentType && (
            <>
              <dt className="text-text-muted">Type</dt>
              <dd>{job.employmentType}</dd>
            </>
          )}
          <dt className="text-text-muted">First seen</dt>
          <dd>
            {formatDateTimeIST(job.firstSeenAt)} (
            {relativeTime(job.firstSeenAt)})
          </dd>
          <dt className="text-text-muted">Last seen</dt>
          <dd>
            {formatDateTimeIST(job.lastSeenAt)} ({relativeTime(job.lastSeenAt)})
          </dd>
        </dl>

        {job.skills.length > 0 && (
          <ul className="flex flex-wrap gap-1.5 text-xs" aria-label="Skills">
            {job.skills.map((skill) => (
              <li
                key={skill}
                className="rounded-md bg-muted px-1.5 py-0.5 text-text-muted"
              >
                {skill}
              </li>
            ))}
          </ul>
        )}

        {job.summary && (
          <section aria-labelledby="summary-heading">
            <h2 id="summary-heading" className="mb-1 text-sm font-semibold">
              Summary
            </h2>
            <p className="text-sm whitespace-pre-line">{job.summary}</p>
          </section>
        )}

        <SourceLinks job={job} names={names} />

        <div className="flex gap-2 pt-1">
          <ApplyLink job={job} className="flex-[1.3]" />
          <TriageActions jobId={job.id} title={job.title} status={job.status} />
        </div>
      </article>

      <section
        aria-labelledby="application-heading"
        className={`${card} p-4 sm:p-6`}
      >
        <h2 id="application-heading" className="mb-4 text-lg font-semibold">
          Application
        </h2>
        <ApplicationForm
          jobId={job.id}
          today={todayIST()}
          initial={{
            status: job.status,
            applied_on: job.appliedOn ?? "",
            resume_version: job.resumeVersion ?? "",
            referral_contact: job.referralContact ?? "",
            notes: job.notes ?? "",
          }}
        />
      </section>
    </div>
  );
}
