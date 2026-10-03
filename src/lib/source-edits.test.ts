import { describe, expect, it } from "vitest";
import {
  deriveSourceId,
  sameSiteSource,
  sourceUpdatePayload,
  templateChanged,
  type SourceOverride,
} from "./source-edits";

describe("deriveSourceId", () => {
  it("slugs a plain name", () => {
    expect(deriveSourceId("Instahyre", "https://www.instahyre.com", [])).toBe(
      "instahyre",
    );
  });

  it("turns punctuation and spaces into single hyphens", () => {
    expect(
      deriveSourceId("  Welcome to the Jungle! ", "https://x.com", []),
    ).toBe("welcome-to-the-jungle");
  });

  it("drops accents", () => {
    expect(deriveSourceId("Café Jobs", "https://x.com", [])).toBe("cafe-jobs");
  });

  it("cuts to 40 characters without a trailing hyphen", () => {
    const id = deriveSourceId(`${"a".repeat(39)} b`, "https://x.com", []);
    expect(id).toBe("a".repeat(39));
  });

  it("falls back to the host without www.", () => {
    expect(deriveSourceId("★", "https://www.foundit.in", [])).toBe(
      "foundit-in",
    );
  });

  it("appends -2 … -9 when taken", () => {
    expect(
      deriveSourceId("Instahyre", "https://jobs.instahyre.in", ["instahyre"]),
    ).toBe("instahyre-2");
    expect(
      deriveSourceId("Instahyre", "https://x.com", [
        "instahyre",
        "instahyre-2",
        "instahyre-3",
      ]),
    ).toBe("instahyre-4");
  });

  it("keeps a suffixed id within 40 characters", () => {
    const long = "b".repeat(40);
    expect(deriveSourceId(long, "https://x.com", [long])).toBe(
      `${"b".repeat(38)}-2`,
    );
  });

  it("returns null when every suffix is taken", () => {
    const taken = ["acme", ...[2, 3, 4, 5, 6, 7, 8, 9].map((n) => `acme-${n}`)];
    expect(deriveSourceId("Acme", "https://acme.com", taken)).toBeNull();
  });

  it("returns null when neither name nor host gives an id", () => {
    expect(deriveSourceId("★", "not a url", [])).toBeNull();
  });
});

describe("sameSiteSource", () => {
  const sources = [
    { name: "Himalayas", base_url: "https://himalayas.app" },
    { name: "WTTJ", base_url: "https://www.welcometothejungle.com/en" },
  ];

  it("matches the same host on another path", () => {
    expect(sameSiteSource("https://himalayas.app/jobs", sources)?.name).toBe(
      "Himalayas",
    );
  });

  it("ignores www. and case", () => {
    expect(
      sameSiteSource("https://WelcomeToTheJungle.com", sources)?.name,
    ).toBe("WTTJ");
  });

  it("does not match a different subdomain", () => {
    expect(sameSiteSource("https://jobs.himalayas.app", sources)).toBeNull();
  });

  it("returns null for an invalid URL", () => {
    expect(sameSiteSource("nope", sources)).toBeNull();
  });
});

describe("sourceUpdatePayload", () => {
  const plain = {
    name: "Himalayas",
    base_url: "https://himalayas.app",
    requires_login: false,
    enabled: true,
    notes: null,
  };
  const unchanged: SourceOverride = {
    access_method: "public_scrape",
    search_url_template: "https://himalayas.app/jobs/{page}",
    orig_access_method: "public_scrape",
    orig_search_url_template: "https://himalayas.app/jobs/{page}",
  };

  it("writes only the plain fields when the override is unchanged", () => {
    expect(sourceUpdatePayload(plain, unchanged)).toEqual(plain);
    expect(templateChanged(unchanged)).toBe(false);
  });

  it("writes a changed access method alone", () => {
    expect(
      sourceUpdatePayload(plain, { ...unchanged, access_method: "rss" }),
    ).toEqual({ ...plain, access_method: "rss" });
  });

  it("marks a changed template as manual and unverified", () => {
    const override = {
      ...unchanged,
      search_url_template: "https://himalayas.app/jobs?q={query}",
    };
    expect(templateChanged(override)).toBe(true);
    expect(sourceUpdatePayload(plain, override)).toEqual({
      ...plain,
      search_url_template: "https://himalayas.app/jobs?q={query}",
      template_origin: "manual",
      template_status: "unverified",
      template_verified_at: null,
    });
  });

  it("clears the template for the trigger to learn again", () => {
    expect(
      sourceUpdatePayload(plain, { ...unchanged, search_url_template: "  " }),
    ).toEqual({
      ...plain,
      search_url_template: null,
      template_origin: null,
      template_status: "unverified",
      template_verified_at: null,
    });
  });

  it("ignores whitespace-only differences", () => {
    expect(
      sourceUpdatePayload(plain, {
        ...unchanged,
        search_url_template: ` ${unchanged.search_url_template} `,
      }),
    ).toEqual(plain);
  });
});
