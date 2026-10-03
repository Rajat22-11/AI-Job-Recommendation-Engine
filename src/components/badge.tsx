import type { ReactNode } from "react";

const tones = {
  neutral: "bg-muted text-text-muted",
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
} as const;

export type BadgeTone = keyof typeof tones;

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: BadgeTone;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-xs font-medium whitespace-nowrap ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
