"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import {
  applicationFormSchema,
  applicationSnapshot,
  type ApplicationSnapshot,
} from "@/lib/application-schemas";
import {
  QUICK_ACTIONS,
  quickActionPlan,
  statusChangePlan,
  type ApplicationPlan,
} from "@/lib/applications";
import { assertSession } from "@/lib/auth/session";
import { todayIST } from "@/lib/dates";
import { db } from "@/lib/db/client";
import { APP_STATUSES, type FeedStatus } from "@/lib/db/domain";

const jobIdSchema = z.uuid();

async function currentApplication(
  jobId: string,
): Promise<ApplicationSnapshot | null> {
  const { data, error } = await db()
    .from("applications")
    .select("*")
    .eq("job_id", jobId)
    .maybeSingle();
  if (error) throw error;
  return data ? applicationSnapshot.parse(data) : null;
}

async function applyPlan(
  jobId: string,
  plan: ApplicationPlan,
): Promise<FeedStatus> {
  if (plan.kind === "delete") {
    const { error } = await db()
      .from("applications")
      .delete()
      .eq("job_id", jobId);
    if (error) throw error;
    return "new";
  }
  // Only the listed columns are written, so notes and other fields survive.
  const { error } = await db()
    .from("applications")
    .upsert(
      {
        job_id: jobId,
        status: plan.status,
        updated_at: new Date().toISOString(),
        ...(plan.applied_on ? { applied_on: plan.applied_on } : {}),
      },
      { onConflict: "job_id" },
    );
  if (error) throw error;
  return plan.status;
}

function revalidateAll() {
  revalidatePath("/", "layout");
}

export type QuickActionResult =
  | { ok: true; status: FeedStatus; previous: ApplicationSnapshot | null }
  | { ok: false; error: string };

/** One-tap Save / Applied / Skip / Unsave. Returns the previous row for Undo. */
export async function quickAction(
  jobId: string,
  action: string,
): Promise<QuickActionResult> {
  await assertSession();
  const id = jobIdSchema.safeParse(jobId);
  const act = z.enum(QUICK_ACTIONS).safeParse(action);
  if (!id.success || !act.success)
    return { ok: false, error: "Invalid request" };

  try {
    const previous = await currentApplication(id.data);
    const status = await applyPlan(
      id.data,
      quickActionPlan(act.data, previous, todayIST()),
    );
    revalidateAll();
    return { ok: true, status, previous };
  } catch (error) {
    console.error("quickAction failed", error);
    return { ok: false, error: "Couldn't update the job. Try again." };
  }
}

/** No-JavaScript fallback for the quick action buttons. */
export async function quickActionForm(formData: FormData): Promise<void> {
  const result = await quickAction(
    String(formData.get("jobId")),
    String(formData.get("action")),
  );
  if (!result.ok) throw new Error(result.error);
}

/** Undo: put back exactly the row that existed before (or none). */
export async function restoreApplication(
  jobId: string,
  previous: ApplicationSnapshot | null,
): Promise<{ ok: boolean }> {
  await assertSession();
  const id = jobIdSchema.safeParse(jobId);
  if (!id.success) return { ok: false };

  try {
    if (previous === null) {
      const { error } = await db()
        .from("applications")
        .delete()
        .eq("job_id", id.data);
      if (error) throw error;
    } else {
      const row = applicationSnapshot.parse(previous);
      if (row.job_id !== id.data) return { ok: false };
      const { error } = await db()
        .from("applications")
        .upsert(row, { onConflict: "job_id" });
      if (error) throw error;
    }
    revalidateAll();
    return { ok: true };
  } catch (error) {
    console.error("restoreApplication failed", error);
    return { ok: false };
  }
}

/** Tracker: move an application to another status. */
export async function moveApplication(formData: FormData): Promise<void> {
  await assertSession();
  const id = jobIdSchema.parse(formData.get("jobId"));
  const status = z.enum(APP_STATUSES).parse(formData.get("status"));
  const existing = await currentApplication(id);
  await applyPlan(id, statusChangePlan(status, existing, todayIST()));
  revalidateAll();
}

export type ApplicationFormField =
  "status" | "applied_on" | "resume_version" | "referral_contact" | "notes";

export interface ApplicationFormState {
  /** Set on every response so the form remounts after each submission. */
  at?: number;
  saved?: boolean;
  needsConfirm?: boolean;
  formError?: string;
  errors?: Partial<Record<ApplicationFormField, string>>;
  values?: Partial<Record<ApplicationFormField, string>>;
}

/** Job detail: create, update or (after confirmation) delete the application. */
export async function saveApplication(
  prev: ApplicationFormState,
  formData: FormData,
): Promise<ApplicationFormState> {
  return { ...(await saveApplicationFields(prev, formData)), at: Date.now() };
}

async function saveApplicationFields(
  _prev: ApplicationFormState,
  formData: FormData,
): Promise<ApplicationFormState> {
  await assertSession();
  const fields: ApplicationFormField[] = [
    "status",
    "applied_on",
    "resume_version",
    "referral_contact",
    "notes",
  ];
  const values = Object.fromEntries(
    fields.map((f) => [f, String(formData.get(f) ?? "")]),
  ) as Record<ApplicationFormField, string>;

  const id = jobIdSchema.safeParse(formData.get("jobId"));
  if (!id.success) return { formError: "Invalid job", values };

  const today = todayIST();
  const parsed = applicationFormSchema(today).safeParse(values);
  if (!parsed.success) {
    const errors: ApplicationFormState["errors"] = {};
    for (const issue of parsed.error.issues) {
      const field = issue.path[0] as ApplicationFormField;
      errors[field] ??= issue.message;
    }
    return { errors, values };
  }
  const form = parsed.data;

  try {
    if (form.status === "new") {
      const existing = await currentApplication(id.data);
      if (existing && formData.get("confirmReset") !== "yes") {
        return { needsConfirm: true, values };
      }
      await applyPlan(id.data, { kind: "delete" });
    } else {
      const { error } = await db()
        .from("applications")
        .upsert(
          {
            job_id: id.data,
            status: form.status,
            applied_on:
              form.status === "applied" && !form.applied_on
                ? today
                : form.applied_on,
            resume_version: form.resume_version,
            referral_contact: form.referral_contact,
            notes: form.notes,
            updated_at: new Date().toISOString(),
          },
          { onConflict: "job_id" },
        );
      if (error) throw error;
    }
  } catch (error) {
    console.error("saveApplication failed", error);
    return { formError: "Couldn't save. Try again.", values };
  }

  revalidateAll();
  return { saved: true };
}
