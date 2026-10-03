"use client";

import { useActionState } from "react";
import {
  saveApplication,
  type ApplicationFormField,
  type ApplicationFormState,
} from "@/lib/actions/applications";
import { FEED_STATUSES, STATUS_LABELS } from "@/lib/db/domain";
import {
  btnDanger,
  btnPrimary,
  btnSecondary,
  fieldError,
  input,
  label,
} from "@/components/ui";

export function ApplicationForm({
  jobId,
  initial,
  today,
}: {
  jobId: string;
  initial: Record<ApplicationFormField, string>;
  today: string;
}) {
  const [state, action, pending] = useActionState<
    ApplicationFormState,
    FormData
  >(saveApplication, {});
  // After a failed save, keep what the user typed.
  const values = { ...initial, ...state.values };
  const error = (field: ApplicationFormField) => state.errors?.[field];
  const describedBy = (field: ApplicationFormField) =>
    error(field) ? `${field}-error` : undefined;

  return (
    // React resets a form after its action runs, and a <select> ignores later
    // defaultValue changes, so remount the form whenever the values it shows change.
    <form
      key={`${state.at ?? 0}:${JSON.stringify(values)}`}
      action={action}
      className="space-y-4"
    >
      <input type="hidden" name="jobId" value={jobId} />

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="status" className={label}>
            Status
          </label>
          <select
            id="status"
            name="status"
            defaultValue={values.status}
            aria-describedby={describedBy("status")}
            className={input}
          >
            {FEED_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === "new" ? "New (no application)" : STATUS_LABELS[s]}
              </option>
            ))}
          </select>
          {error("status") && (
            <p id="status-error" className={fieldError}>
              {error("status")}
            </p>
          )}
        </div>
        <div>
          <label htmlFor="applied_on" className={label}>
            Applied on
          </label>
          <input
            id="applied_on"
            name="applied_on"
            type="date"
            max={today}
            defaultValue={values.applied_on}
            aria-invalid={error("applied_on") ? true : undefined}
            aria-describedby={describedBy("applied_on")}
            className={input}
          />
          {error("applied_on") && (
            <p id="applied_on-error" className={fieldError}>
              {error("applied_on")}
            </p>
          )}
        </div>
        <div>
          <label htmlFor="resume_version" className={label}>
            Resume version
          </label>
          <input
            id="resume_version"
            name="resume_version"
            maxLength={200}
            defaultValue={values.resume_version}
            aria-describedby={describedBy("resume_version")}
            className={input}
          />
          {error("resume_version") && (
            <p id="resume_version-error" className={fieldError}>
              {error("resume_version")}
            </p>
          )}
        </div>
        <div>
          <label htmlFor="referral_contact" className={label}>
            Referral contact
          </label>
          <input
            id="referral_contact"
            name="referral_contact"
            maxLength={200}
            defaultValue={values.referral_contact}
            aria-describedby={describedBy("referral_contact")}
            className={input}
          />
          {error("referral_contact") && (
            <p id="referral_contact-error" className={fieldError}>
              {error("referral_contact")}
            </p>
          )}
        </div>
      </div>

      <div>
        <label htmlFor="notes" className={label}>
          Notes
        </label>
        <textarea
          id="notes"
          name="notes"
          rows={5}
          defaultValue={values.notes}
          aria-invalid={error("notes") ? true : undefined}
          aria-describedby={describedBy("notes")}
          className={input}
        />
        {error("notes") && (
          <p id="notes-error" className={fieldError}>
            {error("notes")}
          </p>
        )}
      </div>

      <div aria-live="polite">
        {state.formError && (
          <p role="alert" className="text-sm text-danger">
            {state.formError}
          </p>
        )}
        {state.saved && (
          <p className="text-sm font-medium text-success">Saved</p>
        )}
      </div>

      {state.needsConfirm ? (
        <div role="alert" className="space-y-3 rounded-lg bg-danger-soft p-3">
          <p className="text-sm text-danger">
            Resetting to New deletes this application, including its notes,
            resume version and referral contact.
          </p>
          <div className="flex gap-2">
            <button
              type="submit"
              name="confirmReset"
              value="yes"
              disabled={pending}
              className={btnDanger}
            >
              Discard notes and reset
            </button>
            <a href={`/jobs/${jobId}`} className={btnSecondary}>
              Cancel
            </a>
          </div>
        </div>
      ) : (
        <button type="submit" disabled={pending} className={btnPrimary}>
          {pending ? "Saving…" : "Save application"}
        </button>
      )}
    </form>
  );
}
