import { describe, expect, it } from "vitest";
import {
  activeFilterCount,
  DEFAULT_FILTERS,
  feedHref,
  parseFeedParams,
  safeFeedQuery,
  serializeFeedParams,
} from "./params";
import {
  caseVariants,
  postedFilter,
  sanitizeSearch,
  searchFilter,
  sourceFilter,
} from "./query-filters";

describe("parseFeedParams", () => {
  it("returns the default view with no params", () => {
    expect(parseFeedParams({})).toEqual(DEFAULT_FILTERS);
  });

  it("parses a bookmarked view with repeated params", () => {
    const f = parseFeedParams({
      track: "ml_ai",
      loc: ["pune", "remote_india"],
      fit: "4",
      sort: "newest",
    });
    expect(f.track).toEqual(["ml_ai"]);
    expect(f.loc).toEqual(["pune", "remote_india"]);
    expect(f.fit).toBe(4);
    expect(f.sort).toBe("newest");
    expect(f.status).toEqual(["new", "saved"]);
  });

  it("ignores invalid values", () => {
    const f = parseFeedParams({
      fit: "9",
      sort: "random",
      status: "archived",
      track: "frontend",
      posted: "2",
      salary: "high",
      page: "-1",
      source: "Bad Id!",
    });
    expect(f).toEqual(DEFAULT_FILTERS);
  });

  it("supports status=all and fit=0", () => {
    const f = parseFeedParams({ status: ["all", "saved"], fit: "0" });
    expect(f.status).toBe("all");
    expect(f.fit).toBe(0);
  });

  it("reads seen, posted, salary, source and q", () => {
    const f = parseFeedParams({
      seen: "24h",
      posted: "7",
      salary: "unknown",
      source: ["naukri", "naukri", "linkedin"],
      q: "  python  ",
    });
    expect(f.seen24h).toBe(true);
    expect(f.posted).toBe(7);
    expect(f.salary).toBe("unknown");
    expect(f.source).toEqual(["naukri", "linkedin"]);
    expect(f.q).toBe("python");
  });
});

describe("serializeFeedParams", () => {
  it("omits defaults", () => {
    expect(serializeFeedParams(DEFAULT_FILTERS)).toBe("");
  });

  it("round-trips", () => {
    const query =
      "?track=ml_ai&loc=pune&loc=remote_india&status=applied&fit=4&sort=newest&page=2";
    const parsed = parseFeedParams(Object.fromEntries(group(query)));
    expect(serializeFeedParams(parsed)).toBe(query);
  });
});

describe("feedHref", () => {
  it("resets to page 1 when filters change", () => {
    const f = { ...DEFAULT_FILTERS, page: 3 };
    expect(feedHref(f, { sort: "salary" })).toBe("/?sort=salary");
  });

  it("keeps filters when paging", () => {
    const f = { ...DEFAULT_FILTERS, track: ["data" as const] };
    expect(feedHref(f, { page: 2 })).toBe("/?track=data&page=2");
  });
});

describe("activeFilterCount", () => {
  it("counts only non-default filters", () => {
    expect(activeFilterCount(DEFAULT_FILTERS)).toBe(0);
    expect(activeFilterCount({ ...DEFAULT_FILTERS, sort: "salary" })).toBe(0);
    expect(activeFilterCount({ ...DEFAULT_FILTERS, fit: 0, q: "java" })).toBe(
      2,
    );
  });
});

describe("safeFeedQuery", () => {
  it("accepts feed queries and normalizes them", () => {
    expect(safeFeedQuery("?track=data&page=2")).toBe("?track=data&page=2");
  });

  it("rejects anything else", () => {
    expect(safeFeedQuery("https://evil.example")).toBe("");
    expect(safeFeedQuery(undefined)).toBe("");
  });
});

describe("search filters", () => {
  it("ignores short terms and strips syntax characters", () => {
    expect(sanitizeSearch(" a ")).toBeNull();
    expect(sanitizeSearch("c++, (java)")).toBe("c++ java");
    expect(sanitizeSearch('50%_off*"')).toBe("50 off");
  });

  it("builds case variants for skill matching", () => {
    expect(caseVariants("python")).toEqual(["python", "PYTHON", "Python"]);
  });

  it("builds an or-filter over title, company and skills", () => {
    expect(searchFilter("acme")).toBe(
      'title.ilike."*acme*",company.ilike."*acme*",skills.cs.{"acme"},skills.cs.{"ACME"},skills.cs.{"Acme"}',
    );
  });

  it("builds source and posted filters", () => {
    expect(sourceFilter(["naukri", "linkedin"])).toBe(
      'links.cs.[{"source":"naukri"}],links.cs.[{"source":"linkedin"}]',
    );
    expect(postedFilter(3, new Date("2026-10-03T06:00:00Z"))).toBe(
      "posted_at.gte.2026-09-30,and(posted_at.is.null,first_seen_at.gte.2026-09-30T06:00:00.000Z)",
    );
  });
});

function group(query: string): Map<string, string[]> {
  const grouped = new Map<string, string[]>();
  for (const [k, v] of new URLSearchParams(query))
    grouped.set(k, [...(grouped.get(k) ?? []), v]);
  return grouped;
}
