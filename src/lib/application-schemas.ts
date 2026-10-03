import { z } from "zod";
import { APP_STATUSES, FEED_STATUSES } from "@/lib/db/domain";

const dateString = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

/** A full applications row, as returned for Undo and sent back to restore it. */
export const applicationSnapshot = z.object({
  job_id: z.uuid(),
  status: z.enum(APP_STATUSES),
  applied_on: dateString.nullable(),
  resume_version: z.string().max(200).nullable(),
  referral_contact: z.string().max(200).nullable(),
  notes: z.string().max(5000).nullable(),
  updated_at: z.string(),
});
export type ApplicationSnapshot = z.infer<typeof applicationSnapshot>;

const optionalText = (max: number, name: string) =>
  z
    .string()
    .trim()
    .max(max, `${name} must be at most ${max} characters`)
    .transform((v) => v || null);

/** The job detail application form. `today` bounds the applied-on date. */
export function applicationFormSchema(today: string) {
  return z.object({
    status: z.enum(FEED_STATUSES, "Choose a status"),
    applied_on: z
      .string()
      .trim()
      .refine(
        (v) => v === "" || dateString.safeParse(v).success,
        "Enter a valid date",
      )
      .refine((v) => v === "" || v <= today, "Date can't be in the future")
      .transform((v) => v || null),
    resume_version: optionalText(200, "Resume version"),
    referral_contact: optionalText(200, "Referral contact"),
    notes: optionalText(5000, "Notes"),
  });
}
export type ApplicationFormValues = z.infer<
  ReturnType<typeof applicationFormSchema>
>;
