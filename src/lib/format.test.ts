import { describe, expect, it } from "vitest";
import {
  formatFit,
  formatPosted,
  formatSalary,
  formatSalaryRange,
  formatYoe,
  isNewJob,
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
  it("falls back when undisclosed", () => {
    expect(formatSalary(null)).toBe("Salary not disclosed");
    expect(formatSalary("  ")).toBe("Salary not disclosed");
    expect(formatSalary("₹12–18 LPA")).toBe("₹12–18 LPA");
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
