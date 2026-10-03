"use client";

import "./globals.css";

export default function GlobalError({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    // Replaces the root layout, so it cannot read the theme cookie: dark default.
    <html lang="en" data-theme="dark" style={{ colorScheme: "dark" }}>
      <body>
        <main className="mx-auto max-w-md px-4 py-16 text-center">
          <h1 className="mb-2 text-xl font-semibold">Something went wrong</h1>
          <p className="mb-6 text-text-muted">
            The app hit an unexpected error.
          </p>
          <button
            type="button"
            onClick={reset}
            className="tap rounded-lg bg-accent px-4 text-sm font-medium text-on-accent"
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
