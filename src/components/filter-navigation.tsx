"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useTransition,
} from "react";
import type { ComponentProps, ReactNode } from "react";
import type { Route } from "next";

interface FilterNavigation {
  /** True from the moment a filter navigation starts until its results render. */
  pending: boolean;
  /** Swap the feed URL in place: no history entry, no scroll. */
  navigate: (href: string) => void;
}

const FilterNavigationContext = createContext<FilterNavigation>({
  pending: false,
  navigate: () => {},
});

export function useFilterNavigation(): FilterNavigation {
  return useContext(FilterNavigationContext);
}

// Wraps the filter panel and the results so the panel can start a navigation
// and the results can show that one is running.
export function FilterNavigationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const navigate = useCallback(
    (href: string) => {
      startTransition(() => {
        router.replace(href as Route, { scroll: false });
      });
    },
    [router],
  );

  const value = useMemo(() => ({ pending, navigate }), [pending, navigate]);
  return (
    <FilterNavigationContext.Provider value={value}>
      {children}
    </FilterNavigationContext.Provider>
  );
}

/** A feed link that applies in place, with pending feedback, like a filter. */
export function FilterLink({
  href,
  onClick,
  ...props
}: Omit<ComponentProps<typeof Link>, "href"> & { href: string }) {
  const { navigate } = useFilterNavigation();
  return (
    <Link
      {...props}
      href={href as Route}
      scroll={false}
      onClick={(event) => {
        onClick?.(event);
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return;
        }
        event.preventDefault();
        navigate(href);
      }}
    />
  );
}

/** Spinner next to the result count; announced politely, gone when done. */
export function FilterSpinner() {
  const { pending } = useFilterNavigation();
  if (!pending) return null;
  return (
    <span role="status" className="inline-flex items-center gap-1.5 text-sm">
      <span
        aria-hidden="true"
        className="size-4 animate-spin rounded-full border-2 border-border-strong border-t-accent motion-reduce:animate-none"
      />
      <span className="text-text-muted">Updating…</span>
    </span>
  );
}

/** Dims the results while a filter change loads. Links stay clickable. */
export function ResultsBusy({ children }: { children: ReactNode }) {
  const { pending } = useFilterNavigation();
  return (
    <div
      aria-busy={pending}
      className={`transition-opacity ${pending ? "opacity-50" : ""}`}
    >
      {children}
    </div>
  );
}
