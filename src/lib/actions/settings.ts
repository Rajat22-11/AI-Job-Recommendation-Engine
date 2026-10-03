"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { assertSession } from "@/lib/auth/session";
import { db } from "@/lib/db/client";
import { ACCESS_METHODS } from "@/lib/db/domain";
import { SOURCE_ID_PATTERN } from "@/lib/feed/params";
import { isHttpUrl, normalizeList, templateError } from "@/lib/templates";

const UNIQUE_VIOLATION = "23505";

export interface FormState {
  /** Set on every response so the form remounts after each submission. */
  at?: number;
  saved?: boolean;
  savedAt?: string;
  formError?: string;
  errors?: Record<string, string>;
  values?: Record<string, string>;
}

function formValues(
  formData: FormData,
  fields: readonly string[],
): Record<string, string> {
  return Object.fromEntries(
    fields.map((f) => [f, String(formData.get(f) ?? "")]),
  );
}

function fieldErrors(error: z.ZodError): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const issue of error.issues) {
    const field = String(issue.path[0]);
    errors[field] ??= issue.message;
  }
  return errors;
}

const numberIn = (min: number, max: number, name: string, int = false) =>
  z
    .string()
    .trim()
    .min(1, `Enter ${name}`)
    .transform(Number)
    .pipe(
      z
        .number(`Enter a number`)
        .refine((n) => !int || Number.isInteger(n), "Enter a whole number")
        .refine(
          (n) => n >= min && n <= max,
          `Must be between ${min} and ${max}`,
        ),
    );

const searchConfigSchema = z.object({
  keywords: z
    .string()
    .transform(normalizeList)
    .refine((l) => l.length > 0, "Add at least one keyword"),
  locations: z
    .string()
    .transform(normalizeList)
    .refine((l) => l.length > 0, "Add at least one location"),
  excluded_companies: z.string().transform(normalizeList),
  min_salary_lpa: numberIn(0, 1000, "a salary"),
  max_required_yoe: numberIn(0, 50, "years of experience"),
  max_job_age_days: numberIn(1, 365, "a number of days", true),
});

const SEARCH_FIELDS = Object.keys(searchConfigSchema.shape);

async function saveSearchConfigFields(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  await assertSession();
  const values = formValues(formData, SEARCH_FIELDS);
  const parsed = searchConfigSchema.safeParse(values);
  if (!parsed.success) return { errors: fieldErrors(parsed.error), values };

  const savedAt = new Date().toISOString();
  const { error } = await db()
    .from("search_config")
    .update({ ...parsed.data, updated_at: savedAt })
    .eq("id", 1);
  if (error) {
    console.error("saveSearchConfig failed", error);
    return { formError: "Couldn't save. Try again.", values };
  }
  revalidatePath("/settings");
  return { saved: true, savedAt };
}

const sourceSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Enter a name")
    .max(100, "At most 100 characters"),
  base_url: z
    .string()
    .trim()
    .refine(
      isHttpUrl,
      "Enter an absolute http(s) URL, e.g. https://example.com",
    ),
  access_method: z.enum(ACCESS_METHODS, "Choose an access method"),
  search_url_template: z
    .string()
    .trim()
    .superRefine((value, ctx) => {
      const message = value ? templateError(value) : null;
      if (message) ctx.addIssue({ code: "custom", message });
    })
    .transform((v) => v || null),
  requires_login: z.string().transform((v) => v === "on"),
  enabled: z.string().transform((v) => v === "on"),
  notes: z
    .string()
    .trim()
    .max(1000, "At most 1000 characters")
    .transform((v) => v || null),
});

const newSourceSchema = sourceSchema.extend({
  id: z
    .string()
    .trim()
    .regex(SOURCE_ID_PATTERN, "2–40 lowercase letters, digits, - or _"),
});

const SOURCE_FIELDS = [...Object.keys(newSourceSchema.shape)];

async function createSourceFields(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  await assertSession();
  const values = formValues(formData, SOURCE_FIELDS);
  const parsed = newSourceSchema.safeParse(values);
  if (!parsed.success) return { errors: fieldErrors(parsed.error), values };

  const { error } = await db().from("sources").insert(parsed.data);
  if (error?.code === UNIQUE_VIOLATION) {
    return { errors: { id: "A source with this id already exists" }, values };
  }
  if (error) {
    console.error("createSource failed", error);
    return { formError: "Couldn't add the source. Try again.", values };
  }
  revalidatePath("/", "layout");
  return { saved: true };
}

async function updateSourceFields(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  await assertSession();
  const values = formValues(formData, SOURCE_FIELDS);
  const id = String(formData.get("id") ?? "");
  const parsed = sourceSchema.safeParse(values);
  if (!parsed.success) return { errors: fieldErrors(parsed.error), values };

  // The id is never updated: job links and run history refer to it.
  const { error } = await db().from("sources").update(parsed.data).eq("id", id);
  if (error) {
    console.error("updateSource failed", error);
    return { formError: "Couldn't save the source. Try again.", values };
  }
  revalidatePath("/", "layout");
  return { saved: true };
}

export async function toggleSource(formData: FormData): Promise<void> {
  await assertSession();
  const id = z.string().regex(SOURCE_ID_PATTERN).parse(formData.get("id"));
  const enabled = formData.get("enabled") === "true";
  const { error } = await db().from("sources").update({ enabled }).eq("id", id);
  if (error) throw error;
  revalidatePath("/", "layout");
}

export async function saveSearchConfig(
  prev: FormState,
  formData: FormData,
): Promise<FormState> {
  return { ...(await saveSearchConfigFields(prev, formData)), at: Date.now() };
}

export async function createSource(
  prev: FormState,
  formData: FormData,
): Promise<FormState> {
  return { ...(await createSourceFields(prev, formData)), at: Date.now() };
}

export async function updateSource(
  prev: FormState,
  formData: FormData,
): Promise<FormState> {
  return { ...(await updateSourceFields(prev, formData)), at: Date.now() };
}
