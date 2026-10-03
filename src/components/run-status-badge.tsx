import { isOneOf, RUN_STATUS_LABELS, RUN_STATUSES } from "@/lib/db/domain";
import { effectiveRunStatus } from "@/lib/sources";
import { Badge, type BadgeTone } from "@/components/badge";

const RUN_TONES: Record<string, BadgeTone> = {
  ok: "success",
  partial: "warning",
  needs_login: "warning",
  captcha: "warning",
  error: "danger",
  skipped: "neutral",
};

/** A source run's status, showing legacy "PARTIAL:" runs as Partial. */
export function RunStatusBadge({
  status,
  message,
}: {
  status: string;
  message: string | null;
}) {
  const shown = effectiveRunStatus(status, message);
  return (
    <Badge tone={RUN_TONES[shown] ?? "neutral"}>
      {isOneOf(RUN_STATUSES, shown) ? RUN_STATUS_LABELS[shown] : shown}
    </Badge>
  );
}
