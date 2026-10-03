import type { AppStatus } from "@/lib/db/domain";

export const QUICK_ACTIONS = ["save", "apply", "skip", "unsave"] as const;
export type QuickAction = (typeof QUICK_ACTIONS)[number];

export const QUICK_ACTION_STATUS: Record<
  Exclude<QuickAction, "unsave">,
  AppStatus
> = {
  save: "saved",
  apply: "applied",
  skip: "skipped",
};

export interface ExistingApplication {
  applied_on: string | null;
}

export type ApplicationPlan =
  | { kind: "delete" }
  | { kind: "upsert"; status: AppStatus; applied_on?: string };

/**
 * Status change with the shared date rule: moving to Applied fills today's
 * date unless one is already set. Other fields are never touched.
 */
export function statusChangePlan(
  status: AppStatus,
  existing: ExistingApplication | null,
  today: string,
): ApplicationPlan {
  if (status === "applied" && !existing?.applied_on) {
    return { kind: "upsert", status, applied_on: today };
  }
  return { kind: "upsert", status };
}

export function quickActionPlan(
  action: QuickAction,
  existing: ExistingApplication | null,
  today: string,
): ApplicationPlan {
  if (action === "unsave") return { kind: "delete" };
  return statusChangePlan(QUICK_ACTION_STATUS[action], existing, today);
}
