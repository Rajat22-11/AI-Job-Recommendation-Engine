import { describe, expect, it } from "vitest";
import { applicationFormSchema } from "./application-schemas";
import {
  quickActionPlan,
  removesApplication,
  statusChangePlan,
} from "./applications";

const today = "2026-10-03";

describe("quickActionPlan", () => {
  it("sets applied_on to today when applying for the first time", () => {
    expect(quickActionPlan("apply", null, today)).toEqual({
      kind: "upsert",
      status: "applied",
      applied_on: today,
    });
  });

  it("keeps an existing applied_on", () => {
    expect(
      quickActionPlan("apply", { applied_on: "2026-09-01" }, today),
    ).toEqual({
      kind: "upsert",
      status: "applied",
    });
  });

  it("maps save and skip without touching dates", () => {
    expect(quickActionPlan("save", null, today)).toEqual({
      kind: "upsert",
      status: "saved",
    });
    expect(quickActionPlan("skip", { applied_on: null }, today)).toEqual({
      kind: "upsert",
      status: "skipped",
    });
  });

  it("deletes on unsave", () => {
    expect(quickActionPlan("unsave", { applied_on: null }, today)).toEqual({
      kind: "delete",
    });
  });

  it("deletes on restore, so a skipped job is new again", () => {
    expect(quickActionPlan("restore", { applied_on: null }, today)).toEqual({
      kind: "delete",
    });
    expect(removesApplication("restore")).toBe(true);
    expect(removesApplication("skip")).toBe(false);
  });
});

describe("statusChangePlan", () => {
  it("keeps the date when moving applied → interview", () => {
    expect(
      statusChangePlan("interview", { applied_on: "2026-09-20" }, today),
    ).toEqual({
      kind: "upsert",
      status: "interview",
    });
  });
});

describe("applicationFormSchema", () => {
  const schema = applicationFormSchema(today);
  const valid = {
    status: "interview",
    applied_on: "",
    resume_version: " v3 ",
    referral_contact: "",
    notes: "Round 1 on Fri",
  };

  it("normalizes blanks to null and trims", () => {
    const result = schema.parse(valid);
    expect(result).toEqual({
      status: "interview",
      applied_on: null,
      resume_version: "v3",
      referral_contact: null,
      notes: "Round 1 on Fri",
    });
  });

  it("rejects future dates, long notes and bad statuses", () => {
    const result = schema.safeParse({
      ...valid,
      status: "archived",
      applied_on: "2026-10-04",
      notes: "x".repeat(5001),
    });
    expect(result.success).toBe(false);
    const fields = result.error?.issues.map((i) => i.path[0]);
    expect(fields).toEqual(
      expect.arrayContaining(["status", "applied_on", "notes"]),
    );
    expect(
      result.error?.issues.find((i) => i.path[0] === "applied_on")?.message,
    ).toBe("Date can't be in the future");
  });
});
