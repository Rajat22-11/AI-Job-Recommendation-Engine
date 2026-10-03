import type { Metadata } from "next";
import { requireSession } from "@/lib/auth/session";
import { formatDateTimeIST } from "@/lib/dates";
import { db } from "@/lib/db/client";
import { getLatestRun } from "@/lib/db/queries/runs";
import { getSources } from "@/lib/db/queries/sources";
import { lastUsedNote } from "@/lib/runs";
import { templateState, templateStateSummary } from "@/lib/sources";
import { expandTemplate } from "@/lib/templates";
import { card } from "@/components/ui";
import { SearchConfigForm, SourceForm } from "./forms";

export const metadata: Metadata = { title: "Settings" };

async function getSearchConfig() {
  const { data, error } = await db()
    .from("search_config")
    .select("*")
    .eq("id", 1)
    .single();
  if (error) throw error;
  return data;
}

export default async function SettingsPage() {
  await requireSession();
  const [config, sources, latestRun] = await Promise.all([
    getSearchConfig(),
    getSources(),
    getLatestRun(),
  ]);
  const sample = { query: config.keywords[0], location: config.locations[0] };
  const lastUsed = lastUsedNote(latestRun, config.updated_at);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <section
        aria-labelledby="search-heading"
        className={`${card} p-4 sm:p-6`}
      >
        <h2 id="search-heading" className="mb-1 text-lg font-semibold">
          Search
        </h2>
        <p className="mb-4 text-sm text-text-muted">
          What the scraper looks for on its next run.
        </p>
        <SearchConfigForm
          initial={{
            keywords: config.keywords.join("\n"),
            locations: config.locations.join("\n"),
            excluded_companies: config.excluded_companies.join("\n"),
            min_salary_lpa: String(config.min_salary_lpa),
            max_required_yoe: String(config.max_required_yoe),
            max_job_age_days: String(config.max_job_age_days),
            updatedLabel: formatDateTimeIST(config.updated_at),
            updatedAt: config.updated_at,
            lastRun: latestRun && {
              text: lastUsed.text,
              href: `/runs#run-${latestRun.runId}`,
              startedAt: latestRun.startedAt,
            },
          }}
        />
      </section>

      <section aria-labelledby="sources-heading" className="space-y-3">
        <h2 id="sources-heading" className="text-lg font-semibold">
          Sources
        </h2>
        <p className="text-sm text-text-muted">
          Sources can&apos;t be deleted because job links and run history refer
          to them. Disable one to retire it.
        </p>
        {sources.map((source) => (
          <details key={source.id} className={card}>
            <summary className="flex tap cursor-pointer flex-wrap items-center justify-between gap-x-3 px-4 py-2 font-medium">
              <span>{source.name}</span>
              <span className="text-sm font-normal text-text-muted">
                {source.enabled ? "Enabled" : "Disabled"} ·{" "}
                {templateStateSummary(templateState(source))}
              </span>
            </summary>
            <div className="border-t border-border p-4">
              <SourceForm
                example={
                  source.search_url_template && sample.query && sample.location
                    ? expandTemplate(source.search_url_template, {
                        query: sample.query,
                        location: sample.location,
                      })
                    : null
                }
                initial={{
                  id: source.id,
                  name: source.name,
                  base_url: source.base_url,
                  access_method: source.access_method ?? "",
                  search_url_template: source.search_url_template ?? "",
                  requires_login: source.requires_login,
                  enabled: source.enabled,
                  notes: source.notes ?? "",
                }}
              />
            </div>
          </details>
        ))}
        <details className={card}>
          <summary className="flex tap cursor-pointer items-center px-4 font-medium text-accent">
            + Add a source
          </summary>
          <div className="border-t border-border p-4">
            <SourceForm />
          </div>
        </details>
      </section>
    </div>
  );
}
