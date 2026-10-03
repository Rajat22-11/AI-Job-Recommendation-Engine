"use client";

import { useOptimistic, useTransition } from "react";
import type { MouseEvent } from "react";
import {
  quickAction,
  quickActionForm,
  restoreApplication,
} from "@/lib/actions/applications";
import {
  QUICK_ACTION_STATUS,
  removesApplication,
  type QuickAction,
} from "@/lib/applications";
import type { FeedStatus } from "@/lib/db/domain";
import { useToast } from "@/components/toast";

const DONE_MESSAGE: Record<QuickAction, string> = {
  save: "Saved",
  apply: "Marked applied",
  skip: "Skipped",
  unsave: "Removed from saved",
  restore: "Restored",
};

const button =
  "tap inline-flex flex-1 items-center justify-center rounded-lg border px-2 text-sm font-medium transition-colors";
const idle = "border-border-strong bg-surface text-text hover:bg-muted";
const active = "border-accent bg-accent-soft text-accent";

/**
 * Save / Applied / Skip. With JavaScript: optimistic update plus Undo.
 * Without it: a plain form post to the same Server Action.
 */
export function TriageActions({
  jobId,
  title,
  status,
}: {
  jobId: string;
  title: string;
  status: FeedStatus;
}) {
  const [optimisticStatus, setOptimisticStatus] = useOptimistic(status);
  const [, startTransition] = useTransition();
  const toast = useToast();

  function run(event: MouseEvent<HTMLButtonElement>, action: QuickAction) {
    event.preventDefault();
    startTransition(async () => {
      setOptimisticStatus(
        removesApplication(action) ? "new" : QUICK_ACTION_STATUS[action],
      );
      const result = await quickAction(jobId, action);
      if (!result.ok) {
        toast({ message: result.error, tone: "error" });
        return;
      }
      toast({
        message: `${DONE_MESSAGE[action]}: ${title}`,
        undo: async () => {
          const restored = await restoreApplication(jobId, result.previous);
          if (!restored.ok)
            toast({ message: "Couldn't undo. Try again.", tone: "error" });
        },
      });
    });
  }

  const saved = optimisticStatus === "saved";
  const applied = optimisticStatus === "applied";
  const skipped = optimisticStatus === "skipped";

  return (
    <form action={quickActionForm} className="flex flex-1 gap-2">
      <input type="hidden" name="jobId" value={jobId} />
      <button
        type="submit"
        name="action"
        value={saved ? "unsave" : "save"}
        aria-pressed={saved}
        onClick={(e) => run(e, saved ? "unsave" : "save")}
        className={`${button} ${saved ? active : idle}`}
      >
        {saved ? "Saved" : "Save"}
      </button>
      <button
        type="submit"
        name="action"
        value="apply"
        aria-pressed={applied}
        disabled={applied}
        onClick={(e) => run(e, "apply")}
        className={`${button} ${applied ? active : idle}`}
      >
        Applied
      </button>
      {/* A skipped job offers Restore, which makes it new again. */}
      <button
        type="submit"
        name="action"
        value={skipped ? "restore" : "skip"}
        onClick={(e) => run(e, skipped ? "restore" : "skip")}
        className={`${button} ${skipped ? active : idle}`}
      >
        {skipped ? "Restore" : "Skip"}
      </button>
    </form>
  );
}
