import { describe, expect, it } from "vitest";
import {
  addDays,
  formatDate,
  formatDuration,
  isWithin24h,
  relativeDate,
  relativeTime,
  todayIST,
} from "./dates";

describe("todayIST", () => {
  it("uses the IST calendar date just after midnight IST", () => {
    // 00:30 IST on 2026-10-04 is 19:00 UTC on 2026-10-03.
    expect(todayIST(new Date("2026-10-03T19:00:00Z"))).toBe("2026-10-04");
  });

  it("stays on the same date late in the IST evening", () => {
    expect(todayIST(new Date("2026-10-03T18:29:00Z"))).toBe("2026-10-03");
  });
});

describe("addDays", () => {
  it("crosses month boundaries", () => {
    expect(addDays("2026-10-01", -1)).toBe("2026-09-30");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
  });
});

describe("relativeDate", () => {
  const now = new Date("2026-10-03T06:00:00Z");
  it("reads Today, 1d ago and 3d ago", () => {
    expect(relativeDate("2026-10-03", now)).toBe("Today");
    expect(relativeDate("2026-10-02", now)).toBe("1d ago");
    expect(relativeDate("2026-09-30", now)).toBe("3d ago");
  });
});

describe("relativeTime", () => {
  const now = new Date("2026-10-03T12:00:00Z");
  it("scales from minutes to days", () => {
    expect(relativeTime("2026-10-03T11:59:30Z", now)).toBe("just now");
    expect(relativeTime("2026-10-03T11:55:00Z", now)).toBe("5m ago");
    expect(relativeTime("2026-10-03T09:00:00Z", now)).toBe("3h ago");
    expect(relativeTime("2026-10-01T11:00:00Z", now)).toBe("2d ago");
  });
});

describe("isWithin24h", () => {
  const now = new Date("2026-10-03T12:00:00Z");
  it("is true only inside the last 24 hours", () => {
    expect(isWithin24h("2026-10-03T09:00:00Z", now)).toBe(true);
    expect(isWithin24h("2026-10-02T11:59:00Z", now)).toBe(false);
  });
});

describe("formatting", () => {
  it("formats a date-only value without shifting it", () => {
    expect(formatDate("2026-10-03")).toBe("3 Oct 2026");
  });

  it("formats durations", () => {
    expect(formatDuration("2026-10-03T10:00:00Z", "2026-10-03T10:00:42Z")).toBe(
      "42s",
    );
    expect(formatDuration("2026-10-03T10:00:00Z", "2026-10-03T10:04:12Z")).toBe(
      "4m 12s",
    );
  });
});
