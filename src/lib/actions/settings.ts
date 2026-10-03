"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { assertSession } from "@/lib/auth/session";
import { db } from "@/lib/db/client";
import { ACCESS_METHODS, TEMPLATELESS_ACCESS_METHODS } from "@/lib/db/domain";
import { SOURCE_ID_PATTERN } from "@/lib/feed/params";
import {
  deriveSourceId,
  sameSiteSource,
  sourceUpdatePayload,
  templateChanged,
} from "@/lib/source-edits";
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

const newSourceSchema = z.object({
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
  requires_login: z.string().transform((v) => v === "on"),
  notes: z
    .string()
    .trim()
    .max(1000, "At most 1000 characters")
    .transform((v) => v || null),
});

// The override fields are only written when they differ from the hidden
// originals, and only a changed template is validated (a learned one may use
// placeholders the app doesn't know).
const editSourceSchema = newSourceSchema
  .extend({
    enabled: z.string().transform((v) => v === "on"),
    access_method: z.union(
      [z.literal(""), z.enum(ACCESS_METHODS)],
      "Choose an access method",
    ),
    search_url_template: z.string(),
    orig_access_method: z.string(),
    orig_search_url_template: z.string(),
  })
  .superRefine((value, ctx) => {
    const template = value.search_url_template.trim();
    if (!template || !templateChanged(value)) return;
    const message = templateError(template);
    if (message) {
      ctx.addIssue({ code: "custom", message, path: ["search_url_template"] });
    }
  });

const NEW_SOURCE_FIELDS = Object.keys(newSourceSchema.shape);
const EDIT_SOURCE_FIELDS = [
  ...NEW_SOURCE_FIELDS,
  "enabled",
  "access_method",
  "search_url_template",
  "orig_access_method",
  "orig_search_url_template",
];

async function createSourceFields(
  _prev: FormState,
  formData: FormData,
): Promise<FormState> {
  await assertSession();
  const values = formValues(formData, NEW_SOURCE_FIELDS);
  const parsed = newSourceSchema.safeParse(values);
  if (!parsed.success) return { errors: fieldErrors(parsed.error), values };
  const form = parsed.data;

  const { data: existing, error: loadError } = await db()
    .from("sources")
    .select("id, name, base_url");
  if (loadError) {
    console.error("createSource failed", loadError);
    return { formError: "Couldn't add the source. Try again.", values };
  }

  const sameSite = sameSiteSource(form.base_url, existing);
  if (sameSite) {
    return {
      errors: { base_url: `${sameSite.name} already uses this site` },
      values,
    };
  }

  // A new source waits for the trigger to learn its search URL template.
  const insert = (id: string) =>
    db()
      .from("sources")
      .insert({
        ...form,
        id,
        enabled: true,
        access_method: "auto",
        search_url_template: null,
        template_status: "unverified",
        template_origin: null,
      });

  const taken = existing.map((s) => s.id);
  let id = deriveSourceId(form.name, form.base_url, taken);
  let { error } = id ? await insert(id) : { error: null };
  // Another source may have taken the id since it was loaded: try the next one.
  if (id && error?.code === UNIQUE_VIOLATION) {
    id = deriveSourceId(form.name, form.base_url, [...taken, id]);
    ({ error } = id ? await insert(id) : { error: null });
  }
  if (!id) return { errors: { name: "Choose a different name" }, values };
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
  const values = formValues(formData, EDIT_SOURCE_FIELDS);
  const id = String(formData.get("id") ?? "");
  const parsed = editSourceSchema.safeParse(values);
  if (!parsed.success) return { errors: fieldErrors(parsed.error), values };
  const { name, base_url, requires_login, enabled, notes, ...override } =
    parsed.data;

  // The id is never updated: job links and run history refer to it.
  const { error } = await db()
    .from("sources")
    .update(
      sourceUpdatePayload(
        { name, base_url, requires_login, enabled, notes },
        override,
      ),
    )
    .eq("id", id);
  if (error) {
    console.error("updateSource failed", error);
    return { formError: "Couldn't save the source. Try again.", values };
  }
  revalidatePath("/", "layout");
  return { saved: true };
}

/** Ask the trigger to re-verify a source's template on its next run. */
export async function relearnTemplate(formData: FormData): Promise<void> {
  await assertSession();
  const id = z.string().regex(SOURCE_ID_PATTERN).parse(formData.get("id"));
  // Only after a verdict, and never for sources that don't use templates.
  const { error } = await db()
    .from("sources")
    .update({ template_status: "unverified" })
    .eq("id", id)
    .in("template_status", ["verified", "failed"])
    .or(
      `access_method.is.null,access_method.not.in.(${TEMPLATELESS_ACCESS_METHODS.join(",")})`,
    );
  if (error) throw error;
  revalidatePath("/", "layout");
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
