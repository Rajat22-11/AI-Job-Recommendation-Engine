import { describe, expect, it } from "vitest";
import {
  canRelearn,
  effectiveRunStatus,
  emptyRunWarning,
  latestRunBySource,
  loginAlerts,
  queryCoverage,
  templateState,
} from "./sources";

const run = (source_id: string, status: string, started_at: string) => ({
  source_id,
  status,
  started_at,
});

describe("latestRunBySource", () => {
  it("keeps the newest run per source regardless of order", () => {
    const latest = latestRunBySource([
      run("a", "ok", "2026-10-03T08:00:00Z"),
      run("a", "captcha", "2026-10-03T10:00:00Z"),
      run("b", "ok", "2026-10-02T10:00:00Z"),
    ]);
    expect(latest.get("a")?.status).toBe("captcha");
    expect(latest.get("b")?.status).toBe("ok");
  });
});

describe("loginAlerts", () => {
  const sources = [
    { id: "naukri", name: "Naukri", enabled: true },
    { id: "linkedin", name: "LinkedIn", enabled: false },
    { id: "iimjobs", name: "IIMJobs", enabled: true },
  ];

  it("flags enabled sources whose latest run needs login or captcha", () => {
    const alerts = loginAlerts(sources, [
      run("naukri", "captcha", "2026-10-03T10:00:00Z"),
      run("linkedin", "needs_login", "2026-10-03T10:00:00Z"),
      run("iimjobs", "needs_login", "2026-10-02T10:00:00Z"),
      run("iimjobs", "ok", "2026-10-03T10:00:00Z"),
    ]);
    expect(alerts).toEqual([{ id: "naukri", name: "Naukri" }]);
  });

  it("ignores sources with no runs", () => {
    expect(loginAlerts(sources, [])).toEqual([]);
  });
});

describe("effectiveRunStatus", () => {
  it("keeps partial", () => {
    expect(effectiveRunStatus("partial", null)).toBe("partial");
  });

  it("treats ok with a PARTIAL: message as partial, ignoring case", () => {
    expect(effectiveRunStatus("ok", "PARTIAL: 2 of 6 rate limited")).toBe(
      "partial",
    );
    expect(effectiveRunStatus("ok", "partial: page 2 failed")).toBe("partial");
  });

  it("passes other statuses and messages through", () => {
    expect(effectiveRunStatus("ok", "All good, not partial")).toBe("ok");
    expect(effectiveRunStatus("error", "PARTIAL: x")).toBe("error");
    expect(effectiveRunStatus("weird", null)).toBe("weird");
  });
});

describe("templateState", () => {
  const source = {
    access_method: "public_scrape",
    search_url_template: null,
    template_status: "unverified",
    enabled: true,
  };

  it.each(["connector", "api", "rss"])(
    "is not applicable for %s, whatever the status",
    (access_method) => {
      expect(templateState({ ...source, access_method }).kind).toBe(
        "not_applicable",
      );
    },
  );

  it("waits for the first run without a template", () => {
    expect(templateState(source)).toEqual({ kind: "waiting", disabled: false });
    expect(templateState({ ...source, access_method: "auto" }).kind).toBe(
      "waiting",
    );
    expect(templateState({ ...source, template_status: null }).kind).toBe(
      "waiting",
    );
  });

  it("waits to verify an existing template", () => {
    expect(
      templateState({ ...source, search_url_template: "https://x.com/{query}" })
        .kind,
    ).toBe("waiting_to_verify");
  });

  it("is verified or failed from the status", () => {
    expect(templateState({ ...source, template_status: "verified" }).kind).toBe(
      "verified",
    );
    expect(templateState({ ...source, template_status: "failed" }).kind).toBe(
      "failed",
    );
  });

  it("flags a disabled source that is waiting", () => {
    expect(templateState({ ...source, enabled: false })).toEqual({
      kind: "waiting",
      disabled: true,
    });
    expect(
      templateState({ ...source, enabled: false, template_status: "verified" })
        .disabled,
    ).toBe(false);
  });

  it("offers re-learning only after a verdict", () => {
    expect(canRelearn({ kind: "verified", disabled: false })).toBe(true);
    expect(canRelearn({ kind: "failed", disabled: false })).toBe(true);
    expect(canRelearn({ kind: "waiting", disabled: false })).toBe(false);
    expect(canRelearn({ kind: "not_applicable", disabled: false })).toBe(false);
  });
});

describe("emptyRunWarning", () => {
  it("warns from 3 empty runs", () => {
    expect(emptyRunWarning(2)).toBeNull();
    expect(emptyRunWarning(3)).toBe("No jobs found in the last 3 runs");
    expect(emptyRunWarning(7)).toBe("No jobs found in the last 7 runs");
  });
});

describe("queryCoverage", () => {
  it("counts done queries and lists the ones to resume", () => {
    const rows = [
      { id: "1", status: "done" },
      { id: "2", status: "done" },
      { id: "3", status: "rate_limited" },
      { id: "4", status: "pending" },
      { id: "5", status: "skipped" },
      { id: "6", status: "failed" },
    ];
    const coverage = queryCoverage(rows);
    expect(coverage.done).toBe(2);
    expect(coverage.total).toBe(6);
    expect(coverage.unfinished.map((r) => r.id)).toEqual(["3", "4", "6"]);
  });

  it("handles no rows", () => {
    expect(queryCoverage([])).toEqual({ done: 0, total: 0, unfinished: [] });
  });
});
