"use client";

import { useEffect } from "react";
import { btnPrimary } from "@/components/ui";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div role="alert" className="py-16 text-center">
      <h1 className="mb-2 text-xl font-semibold">Something went wrong</h1>
      <p className="mb-6 text-text-muted">
        This screen couldn&apos;t load. The database may be unreachable for a
        moment.
      </p>
      <button type="button" onClick={reset} className={btnPrimary}>
        Try again
      </button>
    </div>
  );
}
