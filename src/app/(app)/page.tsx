import type { Metadata, Route } from "next";
import Link from "next/link";
import { requireSession } from "@/lib/auth/session";
import { getSourceNames } from "@/lib/db/client";
import { countNewToday, getFeedPage } from "@/lib/db/queries/feed";
import {
  activeFilterCount,
  feedHref,
  PAGE_SIZE,
  parseFeedParams,
  serializeFeedParams,
} from "@/lib/feed/params";
import { activeFilterChips } from "@/lib/feed/chips";
import { ActiveFilterChips } from "@/components/active-filter-chips";
import { FilterPanel } from "@/components/filter-panel";
import {
  FilterLink,
  FilterNavigationProvider,
  FilterSpinner,
  ResultsBusy,
} from "@/components/filter-navigation";
import { JobCard } from "@/components/job-card";
import { btnSecondary } from "@/components/ui";

export const metadata: Metadata = { title: "Feed" };

export default async function FeedPage({ searchParams }: PageProps<"/">) {
  await requireSession();
  const filters = parseFeedParams(await searchParams);

  const [{ jobs, total }, newToday, names] = await Promise.all([
    getFeedPage(filters),
    countNewToday(),
    getSourceNames(),
  ]);

  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = serializeFeedParams(filters);
  const sources = [...names].map(([id, name]) => ({ id, name }));
  const href = (changes: Parameters<typeof feedHref>[1]) =>
    feedHref(filters, changes) as Route;

  return (
    <FilterNavigationProvider>
      <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)] lg:items-start">
        <aside aria-label="Filters" className="lg:sticky lg:top-4">
          <FilterPanel filters={filters} sources={sources} />
        </aside>

        <section aria-labelledby="feed-heading" className="min-w-0">
          <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-2">
            <h1 id="feed-heading" className="text-xl font-semibold">
              Jobs
            </h1>
            <p className="text-sm text-text-muted" aria-live="polite">
              {total === 1 ? "1 job" : `${total} jobs`}
            </p>
            <FilterSpinner />
            <FilterLink
              href={href({ seen24h: true, status: ["new"] })}
              className="ml-auto inline-flex min-h-9 items-center rounded-full bg-accent-soft px-3 text-sm font-medium text-accent hover:underline"
            >
              New today ({newToday})
            </FilterLink>
          </div>

          <ActiveFilterChips chips={activeFilterChips(filters, names)} />

          <ResultsBusy>
            {jobs.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border-strong bg-surface p-8 text-center">
                {total > 0 && filters.page > lastPage ? (
                  <>
                    <p className="mb-4 font-medium">
                      There are no jobs on this page.
                    </p>
                    <Link href={href({ page: 1 })} className={btnSecondary}>
                      Go to page 1
                    </Link>
                  </>
                ) : (
                  <>
                    <p className="mb-4 font-medium">
                      No jobs match these filters
                    </p>
                    {activeFilterCount(filters) > 0 || filters.page > 1 ? (
                      <FilterLink href="/" className={btnSecondary}>
                        Reset filters
                      </FilterLink>
                    ) : (
                      <p className="text-sm text-text-muted">
                        New postings appear here after the next scraper run.
                      </p>
                    )}
                  </>
                )}
              </div>
            ) : (
              <ul className="space-y-3">
                {jobs.map((job) => (
                  <li key={job.id}>
                    <JobCard job={job} names={names} from={from} />
                  </li>
                ))}
              </ul>
            )}

            {total > PAGE_SIZE && (
              <nav
                aria-label="Pagination"
                className="mt-4 flex items-center justify-between gap-2"
              >
                {filters.page > 1 ? (
                  <Link
                    href={href({ page: filters.page - 1 })}
                    className={btnSecondary}
                  >
                    ← Previous
                  </Link>
                ) : (
                  <span />
                )}
                <span className="text-sm text-text-muted">
                  Page {Math.min(filters.page, lastPage)} of {lastPage}
                </span>
                {filters.page < lastPage ? (
                  <Link
                    href={href({ page: filters.page + 1 })}
                    className={btnSecondary}
                  >
                    Next →
                  </Link>
                ) : (
                  <span />
                )}
              </nav>
            )}
          </ResultsBusy>
        </section>
      </div>
    </FilterNavigationProvider>
  );
}
