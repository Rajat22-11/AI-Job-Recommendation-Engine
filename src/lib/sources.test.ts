import { describe, expect, it } from "vitest";
import { latestRunBySource, loginAlerts } from "./sources";

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
