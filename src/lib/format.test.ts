import { describe, expect, it } from "vitest";
import {
  formatFit,
  formatPosted,
  formatSalaryRange,
  formatYoe,
  isNewJob,
  salaryDisplay,
  salaryState,
  splitSkills,
} from "./format";

describe("formatYoe", () => {
  it("covers ranges, open ends and missing values", () => {
    expect(formatYoe(1, 3)).toBe("1–3 yrs");
    expect(formatYoe(3, null)).toBe("3+ yrs");
    expect(formatYoe(null, 3)).toBe("Up to 3 yrs");
    expect(formatYoe(2, 2)).toBe("2 yrs");
    expect(formatYoe(1.5, 4)).toBe("1.5–4 yrs");
    expect(formatYoe(null, null)).toBeNull();
  });
});

describe("salary", () => {
  const none = {
    salaryText: null,
    salaryMinLpa: null,
    salaryMaxLpa: null,
    salaryMeetsMin: null,
  };

  it("is not disclosed without text or figures", () => {
    expect(salaryState(none)).toBe("not_disclosed");
    expect(salaryState({ ...none, salaryText: "" })).toBe("not_disclosed");
    expect(salaryState({ ...none, salaryText: "   " })).toBe("not_disclosed");
    expect(salaryDisplay(none)).toBeNull();
  });

  it("is disclosed with figures but no text", () => {
    const job = { ...none, salaryMinLpa: 10, salaryMaxLpa: 14 };
    expect(salaryState(job)).toBe("not_compared");
    expect(salaryDisplay(job)).toBe("₹10–14 LPA");
  });

  it("is not compared when text is given but not checked", () => {
    const job = { ...none, salaryText: " Competitive + ESOPs " };
    expect(salaryState(job)).toBe("not_compared");
    expect(salaryDisplay(job)).toBe("Competitive + ESOPs");
  });

  it("is compared when checked either way", () => {
    const job = { ...none, salaryText: "₹12–18 LPA", salaryMinLpa: 12 };
    expect(salaryState({ ...job, salaryMeetsMin: true })).toBe("compared");
    expect(salaryState({ ...job, salaryMeetsMin: false })).toBe("compared");
    expect(salaryDisplay(job)).toBe("₹12–18 LPA");
  });

  it("formats numeric ranges", () => {
    expect(formatSalaryRange(12, 18)).toBe("₹12–18 LPA");
    expect(formatSalaryRange(10, null)).toBe("₹10 LPA");
    expect(formatSalaryRange(null, null)).toBeNull();
  });
});

describe("fit and dates", () => {
  const now = new Date("2026-10-03T12:00:00Z");

  it("formats fit", () => {
    expect(formatFit(4)).toBe("4/5");
    expect(formatFit(0)).toBe("0/5");
    expect(formatFit(null)).toBe("Not scored");
  });

  it("uses posted date, else first seen", () => {
    expect(formatPosted("2026-09-30", "2026-10-01T00:00:00Z", now)).toBe(
      "3d ago",
    );
    expect(formatPosted(null, "2026-09-30T12:00:00Z", now)).toBe("Seen 3d ago");
  });

  it("flags jobs first seen in the last 24 hours", () => {
    expect(isNewJob("2026-10-03T09:00:00Z", now)).toBe(true);
    expect(isNewJob("2026-10-01T09:00:00Z", now)).toBe(false);
  });
});

describe("splitSkills", () => {
  it("shows six then +N", () => {
    const skills = ["a", "b", "c", "d", "e", "f", "g", "h", "i"];
    expect(splitSkills(skills)).toEqual({
      shown: skills.slice(0, 6),
      extra: 3,
    });
    expect(splitSkills(["a"]).extra).toBe(0);
  });
});
