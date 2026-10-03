"use client";

import type { FilterChip } from "@/lib/feed/chips";
import { FilterLink } from "@/components/filter-navigation";

/** Removable chips for every active non-default filter. */
export function ActiveFilterChips({ chips }: { chips: FilterChip[] }) {
  if (chips.length === 0) return null;
  return (
    <ul aria-label="Active filters" className="mb-3 flex flex-wrap gap-1.5">
      {chips.map((chip) => (
        <li key={chip.key}>
          <FilterLink
            href={chip.href}
            aria-label={`Remove filter: ${chip.label}`}
            className="inline-flex tap items-center gap-1.5 rounded-full border border-border-strong bg-surface px-3 text-sm text-text hover:bg-muted"
          >
            {chip.label}
            <span aria-hidden="true" className="text-text-muted">
              ×
            </span>
          </FilterLink>
        </li>
      ))}
    </ul>
  );
}
