"use client";

import { useActionState } from "react";
import type { ReactNode } from "react";
import {
  createSource,
  saveSearchConfig,
  updateSource,
  type FormState,
} from "@/lib/actions/settings";
import { ACCESS_METHOD_LABELS, ACCESS_METHODS } from "@/lib/db/domain";
import { formatDateTimeIST } from "@/lib/dates";
import { PLACEHOLDER_HELP, TEMPLATE_PLACEHOLDERS } from "@/lib/templates";
import { btnPrimary, fieldError, input, label } from "@/components/ui";

function Field({
  id,
  text,
  error,
  hint,
  children,
}: {
  id: string;
  text: string;
  error?: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className={label}>
        {text}
      </label>
      {hint && (
        <div id={`${id}-hint`} className="mb-1 text-sm text-text-muted">
          {hint}
        </div>
      )}
      {children}
      {error && (
        <p id={`${id}-error`} className={fieldError}>
          {error}
        </p>
      )}
    </div>
  );
}

function aria(id: string, error?: string, hint = false) {
  const ids = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(
    Boolean,
  );
  return {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": ids.length ? ids.join(" ") : undefined,
  } as const;
}

function Status({
  state,
  savedText = "Saved",
}: {
  state: FormState;
  savedText?: string;
}) {
  return (
    <div aria-live="polite" className="text-sm">
      {state.formError && (
        <p role="alert" className="text-danger">
          {state.formError}
        </p>
      )}
      {state.saved && <p className="font-medium text-success">{savedText}</p>}
    </div>
  );
}

export interface SearchConfigValues {
  keywords: string;
  locations: string;
  excluded_companies: string;
  min_salary_lpa: string;
  max_required_yoe: string;
  max_job_age_days: string;
  /** Pre-formatted on the server to avoid hydration differences. */
  updatedLabel: string;
  updatedAt: string;
  /** The most recently started run; its text is pre-formatted on the server. */
  lastRun: { text: string; href: string; startedAt: string } | null;
}

export function SearchConfigForm({ initial }: { initial: SearchConfigValues }) {
  const [state, action, pending] = useActionState<FormState, FormData>(
    saveSearchConfig,
    {},
  );
  const v = { ...initial, ...state.values };
  const e = state.errors ?? {};
  const updatedLabel = state.savedAt
    ? formatDateTimeIST(state.savedAt)
    : initial.updatedLabel;
  const { lastRun } = initial;
  // Recomputed after a save, so the note appears without a reload.
  const changedAfterRun =
    lastRun !== null &&
    Date.parse(state.savedAt ?? initial.updatedAt) >
      Date.parse(lastRun.startedAt);

  return (
    <form
      key={`${state.at ?? 0}:${JSON.stringify(v)}`}
      action={action}
      className="space-y-4"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          id="keywords"
          text="Keywords"
          error={e.keywords}
          hint="One per line"
        >
          <textarea
            name="keywords"
            rows={5}
            defaultValue={v.keywords}
            className={input}
            {...aria("keywords", e.keywords, true)}
          />
        </Field>
        <Field
          id="locations"
          text="Locations"
          error={e.locations}
          hint="One per line"
        >
          <textarea
            name="locations"
            rows={5}
            defaultValue={v.locations}
            className={input}
            {...aria("locations", e.locations, true)}
          />
        </Field>
      </div>
      <Field
        id="excluded_companies"
        text="Excluded companies"
        error={e.excluded_companies}
        hint="One per line"
      >
        <textarea
          name="excluded_companies"
          rows={3}
          defaultValue={v.excluded_companies}
          className={input}
          {...aria("excluded_companies", e.excluded_companies, true)}
        />
      </Field>
      <div className="grid gap-4 sm:grid-cols-3">
        <Field
          id="min_salary_lpa"
          text="Minimum salary (LPA)"
          error={e.min_salary_lpa}
        >
          <input
            name="min_salary_lpa"
            type="number"
            inputMode="decimal"
            step="0.1"
            min={0}
            max={1000}
            defaultValue={v.min_salary_lpa}
            className={input}
            {...aria("min_salary_lpa", e.min_salary_lpa)}
          />
        </Field>
        <Field
          id="max_required_yoe"
          text="Max required YOE"
          error={e.max_required_yoe}
        >
          <input
            name="max_required_yoe"
            type="number"
            inputMode="decimal"
            step="0.5"
            min={0}
            max={50}
            defaultValue={v.max_required_yoe}
            className={input}
            {...aria("max_required_yoe", e.max_required_yoe)}
          />
        </Field>
        <Field
          id="max_job_age_days"
          text="Max job age (days)"
          error={e.max_job_age_days}
        >
          <input
            name="max_job_age_days"
            type="number"
            inputMode="numeric"
            step="1"
            min={1}
            max={365}
            defaultValue={v.max_job_age_days}
            className={input}
            {...aria("max_job_age_days", e.max_job_age_days)}
          />
        </Field>
      </div>
      <Status state={state} />
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save search settings"}
        </button>
        <span className="text-sm text-text-muted">
          Last updated {updatedLabel}
        </span>
        <span className="text-sm text-text-muted">
          {lastRun ? (
            <a href={lastRun.href} className="text-accent hover:underline">
              {lastRun.text}
            </a>
          ) : (
            "Not used by any run yet"
          )}
        </span>
      </div>
      {changedAfterRun && (
        <p className="text-sm text-warning">
          Changed after this run, applies from the next run.
        </p>
      )}
    </form>
  );
}

export interface SourceValues {
  id: string;
  name: string;
  base_url: string;
  /** "" when the source has none. */
  access_method: string;
  search_url_template: string;
  requires_login: boolean;
  enabled: boolean;
  notes: string;
}

const EMPTY_SOURCE: SourceValues = {
  id: "",
  name: "",
  base_url: "",
  access_method: "",
  search_url_template: "",
  requires_login: false,
  enabled: true,
  notes: "",
};

function TemplateHint({ example }: { example?: string | null }) {
  return (
    <>
      <p>
        Leave unchanged to keep the current template. A new template is marked
        manual and checked on the next run. Clear it to have the template
        learned again. Placeholders:
      </p>
      <ul className="list-disc pl-5">
        {TEMPLATE_PLACEHOLDERS.map((p) => (
          <li key={p}>
            <code className="text-text">{`{${p}}`}</code>: {PLACEHOLDER_HELP[p]}
          </li>
        ))}
      </ul>
      {example && (
        <p className="mt-1 break-all">
          Example: <code className="text-text">{example}</code>
        </p>
      )}
    </>
  );
}

/** Add a source (no `initial`) or edit one (id read-only). */
export function SourceForm({
  initial,
  example,
}: {
  initial?: SourceValues;
  /** Saved template expanded with the first keyword and location. */
  example?: string | null;
}) {
  const editing = initial !== undefined;
  const [state, action, pending] = useActionState<FormState, FormData>(
    editing ? updateSource : createSource,
    {},
  );
  const base = initial ?? EMPTY_SOURCE;
  // Checkbox values come back as "on" / "" after a failed save.
  const v = state.values
    ? {
        ...base,
        ...state.values,
        requires_login: state.values.requires_login === "on",
        enabled: editing ? state.values.enabled === "on" : true,
      }
    : base;
  const e = state.errors ?? {};
  const p = editing ? `src-${base.id}-` : "new-";
  // Keep the override open when it has an error to show.
  const overrideOpen = Boolean(e.access_method || e.search_url_template);

  return (
    // Remount on new values so selects and checkboxes show them (see ApplicationForm).
    <form
      key={`${state.at ?? 0}:${JSON.stringify(v)}`}
      action={action}
      className="space-y-4"
    >
      {editing && (
        <div>
          <span className={label}>Id</span>
          <input type="hidden" name="id" value={base.id} />
          <p className="text-sm">
            <code>{base.id}</code>{" "}
            <span className="text-text-muted">(can&apos;t be changed)</span>
          </p>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id={`${p}name`} text="Name" error={e.name}>
          <input
            name="name"
            defaultValue={v.name}
            className={input}
            {...aria(`${p}name`, e.name)}
          />
        </Field>
        <Field id={`${p}base_url`} text="Base URL" error={e.base_url}>
          <input
            name="base_url"
            type="url"
            defaultValue={v.base_url}
            className={input}
            {...aria(`${p}base_url`, e.base_url)}
          />
        </Field>
      </div>
      {!editing && (
        <p className="text-sm text-text-muted">
          The search URL template is learned automatically on the next run.
        </p>
      )}
      <div className="flex flex-wrap gap-4">
        <label className="flex tap items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="requires_login"
            defaultChecked={v.requires_login}
            className="size-5 accent-accent"
          />
          Requires login
        </label>
        {editing && (
          <label className="flex tap items-center gap-2 text-sm">
            <input
              type="checkbox"
              name="enabled"
              defaultChecked={v.enabled}
              className="size-5 accent-accent"
            />
            Enabled
          </label>
        )}
      </div>
      <Field id={`${p}notes`} text="Notes (optional)" error={e.notes}>
        <textarea
          name="notes"
          rows={2}
          defaultValue={v.notes}
          className={input}
          {...aria(`${p}notes`, e.notes)}
        />
      </Field>
      {editing && (
        <details
          open={overrideOpen}
          className="rounded-lg border border-border"
        >
          <summary className="flex tap cursor-pointer items-center px-3 text-sm font-medium">
            Advanced override
          </summary>
          <div className="space-y-4 border-t border-border p-3">
            <input
              type="hidden"
              name="orig_access_method"
              value={base.access_method}
            />
            <input
              type="hidden"
              name="orig_search_url_template"
              value={base.search_url_template}
            />
            <Field
              id={`${p}access_method`}
              text="Access method"
              error={e.access_method}
            >
              <select
                name="access_method"
                defaultValue={v.access_method}
                className={input}
                {...aria(`${p}access_method`, e.access_method)}
              >
                {base.access_method === "" && <option value="">Not set</option>}
                {ACCESS_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {ACCESS_METHOD_LABELS[m]}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              id={`${p}search_url_template`}
              text="Search URL template"
              error={e.search_url_template}
              hint={<TemplateHint example={example} />}
            >
              <input
                name="search_url_template"
                defaultValue={v.search_url_template}
                className={input}
                {...aria(
                  `${p}search_url_template`,
                  e.search_url_template,
                  true,
                )}
              />
            </Field>
          </div>
        </details>
      )}
      <Status state={state} savedText={editing ? "Saved" : "Source added"} />
      <button type="submit" disabled={pending} className={btnPrimary}>
        {pending ? "Saving…" : editing ? "Save source" : "Add source"}
      </button>
    </form>
  );
}
