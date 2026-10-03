import { describe, expect, it } from "vitest";
import {
  activeFilterCount,
  DEFAULT_FILTERS,
  feedQueryFromForm,
  feedHref,
  hiddenSkippedText,
  hidesSkipped,
  NEW_TODAY_FILTERS,
  NEW_TODAY_HREF,
  parseFeedParams,
  safeFeedQuery,
  serializeFeedParams,
  showSkippedHref,
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

describe("feedQueryFromForm", () => {
  const form = (entries: [string, string][]) => {
    const data = new FormData();
    for (const [key, value] of entries) data.append(key, value);
    return data;
  };

  it("is empty for the default view", () => {
    expect(
      feedQueryFromForm(
        form([
          ["q", ""],
          ["sort", "fit"],
          ["status", "new"],
          ["status", "saved"],
          ["fit", "3"],
          ["salary", "any"],
          ["posted", ""],
        ]),
      ),
    ).toBe("");
  });

  it("repeats keys for checkbox groups", () => {
    expect(
      feedQueryFromForm(
        form([
          ["loc", "pune"],
          ["loc", "remote_india"],
          ["sort", "newest"],
        ]),
      ),
    ).toBe("?loc=pune&loc=remote_india&sort=newest");
  });

  it("keeps the 24h preset from the hidden input and never emits page", () => {
    expect(
      feedQueryFromForm(
        form([
          ["seen", "24h"],
          ["page", "4"],
        ]),
      ),
    ).toBe("?seen=24h");
  });

  it("drops invalid values the way the URL parser does", () => {
    expect(
      feedQueryFromForm(
        form([
          ["fit", "9"],
          ["sort", "random"],
        ]),
      ),
    ).toBe("");
  });

  it("round-trips through the parser", () => {
    const query = feedQueryFromForm(
      form([
        ["track", "ml_ai"],
        ["fit", "4"],
        ["q", " python "],
      ]),
    );
    expect(query).toBe("?track=ml_ai&fit=4&q=python");
  });
});

describe("salary filter values", () => {
  it.each(["meets", "not_disclosed", "unparsed", "unknown"] as const)(
    "round-trips salary=%s",
    (salary) => {
      const f = parseFeedParams({ salary });
      expect(f.salary).toBe(salary);
      expect(serializeFeedParams(f)).toBe(`?salary=${salary}`);
    },
  );
});

describe("hidden skipped jobs", () => {
  it("applies only when the status filter excludes skipped", () => {
    expect(hidesSkipped(DEFAULT_FILTERS)).toBe(true);
    expect(hidesSkipped({ ...DEFAULT_FILTERS, status: "all" })).toBe(false);
    expect(
      hidesSkipped({ ...DEFAULT_FILTERS, status: ["new", "skipped"] }),
    ).toBe(false);
  });

  it("links to the same view with skipped added", () => {
    expect(showSkippedHref(DEFAULT_FILTERS)).toBe(
      "/?status=new&status=saved&status=skipped",
    );
    expect(
      showSkippedHref({ ...DEFAULT_FILTERS, loc: ["pune"], page: 2 }),
    ).toBe("/?loc=pune&status=new&status=saved&status=skipped");
  });

  it("pluralizes the notice", () => {
    expect(hiddenSkippedText(1)).toBe("1 skipped job hidden");
    expect(hiddenSkippedText(4)).toBe("4 skipped jobs hidden");
  });
});

describe("new today preset", () => {
  it("is new jobs first seen in 24h at any fit, ignoring other filters", () => {
    expect(NEW_TODAY_HREF).toBe("/?status=new&fit=0&seen=24h");
    expect(parseFeedParams({ status: "new", fit: "0", seen: "24h" })).toEqual(
      NEW_TODAY_FILTERS,
    );
  });
});
