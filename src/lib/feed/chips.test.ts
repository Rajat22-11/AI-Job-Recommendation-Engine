import { describe, expect, it } from "vitest";
import { activeFilterChips } from "./chips";
import { DEFAULT_FILTERS, parseFeedParams } from "./params";

const names = new Map([["naukri", "Naukri"]]);
const chips = (query: string) =>
  activeFilterChips(
    parseFeedParams(Object.fromEntries(new URLSearchParams(query))),
    names,
  );

describe("activeFilterChips", () => {
  it("shows none for the default view", () => {
    expect(activeFilterChips(DEFAULT_FILTERS, names)).toEqual([]);
  });

  it("never makes a chip for sort or page", () => {
    expect(chips("sort=newest&page=3")).toEqual([]);
  });

  it("makes one chip per non-default value", () => {
    expect(chips("loc=pune&fit=4&q=python").map((c) => c.label)).toEqual([
      '"python"',
      "Pune",
      "Fit 4+",
    ]);
  });

  it("each chip's link drops only its own value", () => {
    const found = Object.fromEntries(
      chips("fit=4&salary=meets&source=naukri").map((c) => [c.key, c.href]),
    );
    expect(found["fit"]).toBe("/?source=naukri&salary=meets");
    expect(found["salary"]).toBe("/?source=naukri&fit=4");
    expect(found["source:naukri"]).toBe("/?fit=4&salary=meets");
  });

  it("falls back to the default statuses when the last status is removed", () => {
    const [chip] = chips("status=applied");
    expect(chip?.label).toBe("Applied");
    expect(chip?.href).toBe("/");
  });

  it("labels the any-status filter", () => {
    const [chip] = chips("status=all");
    expect(chip?.label).toBe("Any status");
    expect(chip?.href).toBe("/");
  });

  it("falls back to the raw id for an unknown source", () => {
    expect(chips("source=other_site")[0]?.label).toBe("other_site");
  });
});

describe("salary chips", () => {
  it.each([
    ["meets", "Meets my minimum"],
    ["not_disclosed", "Salary not disclosed"],
    ["unparsed", "Salary not compared"],
    ["unknown", "Salary unknown"],
  ])("labels salary=%s as %s", (salary, label) => {
    const [chip] = chips(`salary=${salary}`);
    expect(chip?.label).toBe(label);
    expect(chip?.href).toBe("/");
  });
});
