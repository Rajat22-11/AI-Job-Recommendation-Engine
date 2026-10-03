// Shared class strings for buttons and form controls.

const base =
  "tap inline-flex items-center justify-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors disabled:opacity-60";

export const btnPrimary = `${base} bg-accent text-white hover:bg-accent-hover`;
export const btnSecondary = `${base} border border-border-strong bg-surface text-text hover:bg-muted`;
export const btnGhost = `${base} text-text-muted hover:bg-muted hover:text-text`;
export const btnDanger = `${base} border border-danger bg-surface text-danger hover:bg-danger-soft`;

export const input =
  "tap w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-base text-text placeholder:text-text-muted";

export const label = "mb-1 block text-sm font-medium text-text";
export const fieldError = "mt-1 text-sm text-danger";
export const card = "rounded-xl border border-border bg-surface";
