"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  FEED_STATUSES,
  LOCATION_BUCKET_LABELS,
  LOCATION_BUCKETS,
  ROLE_TRACK_LABELS,
  ROLE_TRACKS,
  STATUS_LABELS,
  WORK_MODE_LABELS,
  WORK_MODES,
} from "@/lib/db/domain";
import {
  activeFilterCount,
  POSTED_WITHIN,
  SALARY_FILTER_LABELS,
  SALARY_FILTERS,
  SORT_LABELS,
  SORTS,
  DEFAULT_STATUSES,
  feedQueryFromForm,
  serializeFeedParams,
  type FeedFilters,
} from "@/lib/feed/params";
import {
  FilterLink,
  useFilterNavigation,
} from "@/components/filter-navigation";
import { btnPrimary, btnSecondary, input, label } from "@/components/ui";

interface Option {
  value: string;
  label: string;
}

function CheckboxGroup({
  legend,
  name,
  options,
  selected,
}: {
  legend: string;
  name: string;
  options: Option[];
  selected: readonly string[];
}) {
  return (
    <fieldset>
      <legend className={label}>{legend}</legend>
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => (
          <label
            key={option.value}
            className="flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg border border-border px-2 text-sm has-checked:border-accent has-checked:bg-accent-soft has-checked:text-accent"
          >
            <input
              type="checkbox"
              name={name}
              value={option.value}
              defaultChecked={selected.includes(option.value)}
              className="size-4 accent-accent"
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function Select({
  id,
  name,
  text,
  value,
  options,
}: {
  id: string;
  name: string;
  text: string;
  value: string;
  options: Option[];
}) {
  return (
    <div>
      <label htmlFor={id} className={label}>
        {text}
      </label>
      <select id={id} name={name} defaultValue={value} className={input}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

const toOptions = <T extends string>(
  values: readonly T[],
  labels: Record<T, string>,
) => values.map((value) => ({ value, label: labels[value] }));

// Selects apply at once; checkboxes wait for a run of ticks to finish; search
// waits for a pause in typing (Enter applies immediately).
const SELECT_DELAY_MS = 0;
const CHECKBOX_DELAY_MS = 700;
const TEXT_DELAY_MS = 400;

function delayFor(target: EventTarget): number {
  if (target instanceof HTMLSelectElement) return SELECT_DELAY_MS;
  if (target instanceof HTMLInputElement && target.type === "checkbox") {
    return CHECKBOX_DELAY_MS;
  }
  return TEXT_DELAY_MS;
}

/**
 * Filters apply themselves: any change navigates in place (no history entry,
 * no scroll) after a short debounce. Still a plain GET form underneath, so
 * without JavaScript the noscript button submits it, and a submit leaves out
 * `page` so any filter change goes back to page 1. Collapsed on phones, always
 * open on lg.
 */
export function FilterPanel({
  filters,
  sources,
}: {
  filters: FeedFilters;
  sources: { id: string; name: string }[];
}) {
  const { navigate } = useFilterNavigation();
  const count = activeFilterCount(filters);
  const statuses = filters.status === "all" ? ["all"] : filters.status;
  const queryKey = serializeFeedParams(filters);

  const formRef = useRef<HTMLFormElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  // The inputs are uncontrolled, so they keep the user's focus and scroll
  // position while the URL catches up. When the URL changes for any other
  // reason (a chip, Reset, "New today"), remount the form to show it.
  const [own, setOwn] = useState(queryKey);
  const [sync, setSync] = useState({ query: queryKey, version: 0 });
  if (sync.query !== queryKey) {
    const external = queryKey !== own;
    setSync({ query: queryKey, version: sync.version + (external ? 1 : 0) });
    if (external) setOwn(queryKey);
  }

  useEffect(() => () => clearTimeout(timer.current), []);

  function apply() {
    clearTimeout(timer.current);
    const form = formRef.current;
    if (!form) return;
    let data = new FormData(form);
    if (data.getAll("status").length === 0) {
      // No status ticked means the default view, so show those ticks.
      for (const box of form.querySelectorAll<HTMLInputElement>(
        'input[name="status"]',
      )) {
        box.checked = (DEFAULT_STATUSES as readonly string[]).includes(
          box.value,
        );
      }
      data = new FormData(form);
    }
    const query = feedQueryFromForm(data);
    setOwn(query);
    navigate(`/${query}`);
  }

  function schedule(delay: number) {
    clearTimeout(timer.current);
    if (delay === 0) apply();
    else timer.current = setTimeout(apply, delay);
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    schedule(0);
  }

  return (
    <details className="group rounded-xl border border-border bg-surface lg:[&::details-content]:block lg:[&::details-content]:[content-visibility:visible]">
      <summary className="flex tap cursor-pointer list-none items-center justify-between px-4 font-medium lg:hidden">
        <span>Filters{count > 0 && ` (${count})`}</span>
        <span
          aria-hidden="true"
          className="text-text-muted group-open:rotate-180"
        >
          ▾
        </span>
      </summary>
      <form
        key={sync.version}
        ref={formRef}
        action="/"
        method="get"
        onChange={(event) => schedule(delayFor(event.target))}
        onSubmit={onSubmit}
        className="space-y-4 p-4 pt-2 lg:pt-4"
      >
        <div>
          <label htmlFor="q" className={label}>
            Search
          </label>
          <input
            id="q"
            name="q"
            type="search"
            defaultValue={filters.q}
            placeholder="Title, company or skill"
            className={input}
          />
        </div>

        <Select
          id="sort"
          name="sort"
          text="Sort by"
          value={filters.sort}
          options={toOptions(SORTS, SORT_LABELS)}
        />

        <CheckboxGroup
          legend="Status"
          name="status"
          selected={statuses}
          options={[
            { value: "all", label: "Any status" },
            ...toOptions(FEED_STATUSES, STATUS_LABELS),
          ]}
        />

        <Select
          id="fit"
          name="fit"
          text="Minimum fit"
          value={String(filters.fit)}
          options={[
            { value: "0", label: "Any (incl. unscored)" },
            ...[1, 2, 3, 4, 5].map((n) => ({
              value: String(n),
              label: `${n}+`,
            })),
          ]}
        />

        <CheckboxGroup
          legend="Role track"
          name="track"
          selected={filters.track}
          options={toOptions(ROLE_TRACKS, ROLE_TRACK_LABELS)}
        />
        <CheckboxGroup
          legend="Location"
          name="loc"
          selected={filters.loc}
          options={toOptions(LOCATION_BUCKETS, LOCATION_BUCKET_LABELS)}
        />
        <CheckboxGroup
          legend="Work mode"
          name="mode"
          selected={filters.mode}
          options={toOptions(WORK_MODES, WORK_MODE_LABELS)}
        />

        <Select
          id="salary"
          name="salary"
          text="Salary"
          value={filters.salary}
          options={SALARY_FILTERS.filter(
            // `unknown` is only offered while an old link has it selected.
            (s) => s !== "unknown" || filters.salary === "unknown",
          ).map((s) => ({ value: s, label: SALARY_FILTER_LABELS[s] }))}
        />
        <Select
          id="posted"
          name="posted"
          text="Posted within"
          value={filters.posted === null ? "" : String(filters.posted)}
          options={[
            { value: "", label: "Any time" },
            ...POSTED_WITHIN.map((d) => ({
              value: String(d),
              label: d === 1 ? "1 day" : `${d} days`,
            })),
          ]}
        />

        {sources.length > 0 && (
          <CheckboxGroup
            legend="Source"
            name="source"
            selected={filters.source}
            options={sources.map((s) => ({ value: s.id, label: s.name }))}
          />
        )}

        {filters.seen24h && <input type="hidden" name="seen" value="24h" />}

        <div className="flex gap-2">
          <noscript>
            <button type="submit" className={`${btnPrimary} flex-1`}>
              Apply filters
            </button>
          </noscript>
          <FilterLink
            href="/"
            onClick={() => {
              clearTimeout(timer.current);
              setSync((s) => ({ ...s, version: s.version + 1 }));
            }}
            className={`${btnSecondary} flex-1`}
          >
            Reset filters
          </FilterLink>
        </div>
      </form>
    </details>
  );
}
