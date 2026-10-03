// List-shaped placeholder while a screen's data loads.
export default function Loading() {
  return (
    <div aria-busy="true" aria-label="Loading" className="space-y-3">
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-xl border border-border bg-surface p-4"
        >
          <div className="mb-2 h-4 w-2/3 rounded bg-muted" />
          <div className="mb-3 h-3 w-1/3 rounded bg-muted" />
          <div className="mb-2 flex gap-1.5">
            <div className="h-5 w-14 rounded bg-muted" />
            <div className="h-5 w-14 rounded bg-muted" />
            <div className="h-5 w-16 rounded bg-muted" />
          </div>
          <div className="h-11 rounded-lg bg-muted" />
        </div>
      ))}
    </div>
  );
}
