import type { Metadata, Route } from "next";
import Link from "next/link";
import { moveApplication } from "@/lib/actions/applications";
import { requireSession } from "@/lib/auth/session";
import { formatDate, relativeTime } from "@/lib/dates";
import {
  APP_STATUSES,
  isOneOf,
  STATUS_LABELS,
  type AppStatus,
} from "@/lib/db/domain";
import { getTracker, type TrackerEntry } from "@/lib/db/queries/tracker";
import { Badge } from "@/components/badge";
import { btnSecondary, card } from "@/components/ui";

export const metadata: Metadata = { title: "Tracker" };

function Entry({ entry }: { entry: TrackerEntry }) {
  const selectId = `move-${entry.jobId}`;
  return (
    <li className={`${card} space-y-2 p-3`}>
      <div>
        <Link
          href={`/jobs/${entry.jobId}` as Route}
          className="text-sm leading-snug font-semibold hover:text-accent hover:underline"
        >
          {entry.title}
        </Link>
        <p className="text-sm text-text-muted">{entry.company}</p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-text-muted">
        {!entry.isActive && <Badge tone="danger">Closed</Badge>}
        {entry.appliedOn && <span>Applied {formatDate(entry.appliedOn)}</span>}
        <span>Updated {relativeTime(entry.updatedAt)}</span>
      </div>
      <form action={moveApplication} className="flex gap-1.5 lg:flex-col">
        <input type="hidden" name="jobId" value={entry.jobId} />
        <label htmlFor={selectId} className="sr-only">
          Move {entry.title} to
        </label>
        <select
          id={selectId}
          name="status"
          defaultValue={entry.status}
          className="tap min-w-0 flex-1 rounded-lg border border-border-strong bg-surface px-2 text-sm"
        >
          {APP_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <button type="submit" className={btnSecondary}>
          Move
        </button>
      </form>
    </li>
  );
}

export default async function TrackerPage({
  searchParams,
}: PageProps<"/tracker">) {
  await requireSession();
  const { tab } = await searchParams;
  const selected: AppStatus = isOneOf(APP_STATUSES, tab) ? tab : "applied";
  const groups = await getTracker();
  const total = APP_STATUSES.reduce((sum, s) => sum + groups[s].length, 0);

  if (total === 0) {
    return (
      <div className="py-16 text-center">
        <h1 className="mb-2 text-xl font-semibold">Tracker</h1>
        <p className="mb-6 text-text-muted">
          Jobs you save or apply to will appear here, grouped by status.
        </p>
        <Link href="/" className={btnSecondary}>
          Go to the feed
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-3 text-xl font-semibold">Tracker</h1>

      {/* Phones and tablets: one group at a time, chosen in the URL. */}
      <nav
        aria-label="Status"
        className="-mx-4 mb-3 overflow-x-auto px-4 lg:hidden"
      >
        <ul className="flex gap-1.5">
          {APP_STATUSES.map((s) => (
            <li key={s}>
              <Link
                href={`/tracker?tab=${s}` as Route}
                aria-current={s === selected ? "page" : undefined}
                className={`inline-flex tap items-center gap-1 rounded-full px-3 text-sm font-medium whitespace-nowrap ${
                  s === selected
                    ? "bg-accent text-white"
                    : "border border-border bg-surface text-text-muted"
                }`}
              >
                {STATUS_LABELS[s]} ({groups[s].length})
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="lg:grid lg:grid-cols-6 lg:gap-3">
        {APP_STATUSES.map((s) => (
          <section
            key={s}
            aria-labelledby={`group-${s}`}
            className={s === selected ? "block" : "hidden lg:block"}
          >
            <h2
              id={`group-${s}`}
              className="mb-2 text-sm font-semibold tracking-wide text-text-muted uppercase"
            >
              {STATUS_LABELS[s]} ({groups[s].length})
            </h2>
            {groups[s].length === 0 ? (
              <p className="rounded-xl border border-dashed border-border-strong p-3 text-sm text-text-muted">
                None
              </p>
            ) : (
              <ul className="space-y-2">
                {groups[s].map((entry) => (
                  <Entry key={entry.jobId} entry={entry} />
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
