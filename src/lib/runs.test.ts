import { describe, expect, it } from "vitest";
import {
  diffConfig,
  groupRuns,
  lastUsedNote,
  newJobsTrend,
  snapshotFields,
  type RunRowLike,
  type SourceRunLike,
} from "./runs";

let n = 0;
const sr = (
  run_id: string,
  source_id: string,
  status: string,
  started_at: string,
  extra: Partial<SourceRunLike> = {},
): SourceRunLike => ({
  id: `sr${n++}`,
  run_id,
  source_id,
  status,
  jobs_found: 10,
  jobs_new: 2,
  message: null,
  started_at,
  finished_at: started_at.replace(/:00Z$/, ":30Z"),
  config_snapshot: null,
  ...extra,
});

const run = (run_id: string, extra: Partial<RunRowLike> = {}): RunRowLike => ({
  run_id,
  started_at: "2026-10-03T03:00:00Z",
  finished_at: "2026-10-03T03:20:00Z",
  status: "completed",
  summary: null,
  config_snapshot: null,
  ...extra,
});

describe("groupRuns", () => {
  it("groups source rows by run, summing totals and deriving times", () => {
    const [g] = groupRuns(
      [
        sr("r1", "a", "ok", "2026-10-03T03:05:00Z"),
        sr("r1", "b", "skipped", "2026-10-03T03:01:00Z"),
      ],
      [],
    );
    expect(g).toMatchObject({
      runId: "r1",
      startedAt: "2026-10-03T03:01:00Z",
      finishedAt: "2026-10-03T03:05:30Z",
      status: { label: "OK", tone: "success" },
      found: 20,
      newJobs: 4,
    });
    expect(g?.results.map((r) => r.source_id)).toEqual(["b", "a"]);
  });

  it("needs attention when any source result isn't OK or skipped", () => {
    const [g] = groupRuns(
      [
        sr("r1", "a", "ok", "2026-10-03T03:00:00Z"),
        sr("r1", "b", "ok", "2026-10-03T03:00:00Z", {
          message: "PARTIAL: rate limited",
        }),
      ],
      [],
    );
    expect(g?.status).toEqual({ label: "Needs attention", tone: "warning" });
  });

  it("leaves the finish time empty while a source is still running", () => {
    const [g] = groupRuns(
      [sr("r1", "a", "ok", "2026-10-03T03:00:00Z", { finished_at: null })],
      [],
    );
    expect(g?.finishedAt).toBeNull();
  });

  it("prefers the runs row for times, status, summary and snapshot", () => {
    const [g] = groupRuns(
      [
        sr("r2", "a", "error", "2026-10-03T03:02:00Z", {
          config_snapshot: { min_salary_lpa: 5 },
        }),
      ],
      [
        run("r2", {
          summary: "12 new jobs across 4 sources",
          config_snapshot: { min_salary_lpa: 8.2 },
        }),
      ],
    );
    expect(g).toMatchObject({
      startedAt: "2026-10-03T03:00:00Z",
      finishedAt: "2026-10-03T03:20:00Z",
      status: { label: "completed", tone: "neutral" },
      summary: "12 new jobs across 4 sources",
      snapshot: { min_salary_lpa: 8.2 },
      found: 10,
    });
  });

  it("falls back to the first non-empty source snapshot", () => {
    const [g] = groupRuns(
      [
        sr("r3", "a", "ok", "2026-10-03T03:00:00Z", { config_snapshot: {} }),
        sr("r3", "b", "ok", "2026-10-03T03:01:00Z", {
          config_snapshot: { keywords: ["java"] },
        }),
      ],
      [run("r3", { config_snapshot: null })],
    );
    expect(g?.snapshot).toEqual({ keywords: ["java"] });
  });

  it("includes runs with no source rows, newest first, up to the limit", () => {
    const groups = groupRuns(
      [sr("old", "a", "ok", "2026-10-01T03:00:00Z")],
      [
        run("new", { started_at: "2026-10-03T03:00:00Z" }),
        run("mid", { started_at: "2026-10-02T03:00:00Z" }),
      ],
      2,
    );
    expect(groups.map((g) => g.runId)).toEqual(["new", "mid"]);
    expect(groups[0]?.found).toBe(0);
  });
});

describe("newJobsTrend", () => {
  const today = "2026-10-03";

  it("sums new jobs per IST day and source, newest day first", () => {
    const trend = newJobsTrend(
      [
        sr("r1", "himalayas", "ok", "2026-10-03T03:00:00Z", { jobs_new: 3 }),
        sr("r2", "himalayas", "ok", "2026-10-03T09:00:00Z", { jobs_new: 1 }),
        sr("r2", "wttj", "ok", "2026-10-03T09:00:00Z", { jobs_new: 2 }),
      ],
      today,
    );
    expect(trend.rows).toHaveLength(14);
    expect(trend.rows[0]?.date).toBe("2026-10-03");
    expect(trend.rows[0]?.total).toBe(6);
    expect(Object.fromEntries(trend.rows[0]?.perSource ?? [])).toEqual({
      himalayas: 4,
      wttj: 2,
    });
    expect(trend.sourceIds).toEqual(["himalayas", "wttj"]);
    expect(trend.maxTotal).toBe(6);
  });

  it("leaves days without runs empty", () => {
    const trend = newJobsTrend([], today);
    expect(trend.rows.every((r) => r.total === null)).toBe(true);
    expect(trend.sourceIds).toEqual([]);
    expect(trend.maxTotal).toBe(0);
  });

  it("counts a run by its IST date", () => {
    // 19:00 UTC on 2 Oct is 00:30 IST on 3 Oct.
    const trend = newJobsTrend(
      [sr("r1", "a", "ok", "2026-10-02T19:00:00Z", { jobs_new: 5 })],
      today,
    );
    expect(trend.rows[0]?.total).toBe(5);
    expect(trend.rows[1]?.total).toBeNull();
  });

  it("ignores runs outside the window", () => {
    const trend = newJobsTrend(
      [sr("r1", "a", "ok", "2026-09-19T03:00:00Z")],
      today,
    );
    expect(trend.sourceIds).toEqual([]);
    expect(trend.rows.at(-1)?.date).toBe("2026-09-20");
  });
});

describe("snapshots", () => {
  const current = {
    keywords: ["java developer", "ML engineer"],
    locations: ["Pune"],
    excluded_companies: [],
    min_salary_lpa: 10,
    max_required_yoe: 3,
    max_job_age_days: 30,
  };

  it("shows known fields with Settings labels and keeps unknown keys", () => {
    const fields = snapshotFields({
      keywords: ["java developer"],
      min_salary_lpa: 8.2,
      excluded_companies: [],
      seniority: "entry",
    });
    expect(fields?.known).toEqual([
      { key: "keywords", label: "Keywords", value: "java developer" },
      { key: "excluded_companies", label: "Excluded companies", value: "None" },
      { key: "min_salary_lpa", label: "Minimum salary (LPA)", value: "8.2" },
    ]);
    expect(fields?.extra).toEqual({ seniority: "entry" });
  });

  it("has no fields for an empty or non-object snapshot", () => {
    expect(snapshotFields(null)).toBeNull();
    expect(snapshotFields({})).toBeNull();
    expect(snapshotFields([1, 2])).toBeNull();
    expect(diffConfig(null, current)).toBeNull();
  });

  it("reads the trigger's nested shape", () => {
    const snapshot = {
      sources: ["indeed", "himalayas"],
      search_config: {
        id: 1,
        keywords: ["ML Engineer", "java developer"],
        max_required_yoe: 2,
        updated_at: "2026-10-03T10:29:23Z",
      },
    };
    expect(snapshotFields(snapshot)).toEqual({
      known: [
        {
          key: "keywords",
          label: "Keywords",
          value: "ML Engineer, java developer",
        },
        { key: "max_required_yoe", label: "Max required YOE", value: "2" },
      ],
      extra: {
        updated_at: "2026-10-03T10:29:23Z",
        sources: ["indeed", "himalayas"],
      },
    });
    expect(diffConfig(snapshot, current)).toEqual(["Max required YOE"]);
  });

  it("can't compare a snapshot without known fields", () => {
    expect(diffConfig({ sources: ["indeed"] }, current)).toBeNull();
    expect(snapshotFields({ sources: ["indeed"] })?.known).toEqual([]);
  });

  it("lists the fields that differ from the current settings", () => {
    expect(diffConfig({ min_salary_lpa: 8.2 }, current)).toEqual([
      "Minimum salary (LPA)",
    ]);
  });

  it("compares lists as case-insensitive sets and numbers numerically", () => {
    expect(
      diffConfig(
        {
          keywords: ["ml engineer", "Java Developer", "java developer"],
          max_job_age_days: "30",
          seniority: "anything",
        },
        current,
      ),
    ).toEqual([]);
    expect(diffConfig({ locations: ["Pune", "Mumbai"] }, current)).toEqual([
      "Locations",
    ]);
  });
});

describe("lastUsedNote", () => {
  const latest = {
    runId: "1a2b3c4d-0000-0000-0000-000000000000",
    startedAt: "2026-10-03T03:30:00Z",
  };

  it("says when no run has used the settings", () => {
    expect(lastUsedNote(null, "2026-10-01T00:00:00Z")).toEqual({
      text: "Not used by any run yet",
      changedAfter: false,
    });
  });

  it("names the latest run in IST", () => {
    const note = lastUsedNote(latest, "2026-10-01T00:00:00Z");
    expect(note.text).toMatch(/^Last used by run 1a2b3c4d at 3 Oct 2026, 9:00/);
    expect(note.changedAfter).toBe(false);
  });

  it("flags settings saved after the run started", () => {
    expect(lastUsedNote(latest, "2026-10-03T03:31:00Z").changedAfter).toBe(
      true,
    );
  });
});
