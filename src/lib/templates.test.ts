import { describe, expect, it } from "vitest";
import {
  expandTemplate,
  findUnknownPlaceholders,
  normalizeList,
  templateError,
} from "./templates";

describe("expandTemplate", () => {
  it("matches the settings spec example", () => {
    expect(
      expandTemplate(
        "https://example.com/jobs/{query_slug}-jobs-in-{location}",
        {
          query: "Java Developer",
          location: "Pune",
        },
      ),
    ).toBe("https://example.com/jobs/java-developer-jobs-in-Pune");
  });

  it("URL-encodes query and location", () => {
    expect(
      expandTemplate("https://x.com/s?q={query}&l={location}", {
        query: "ML Engineer",
        location: "Navi Mumbai",
      }),
    ).toBe("https://x.com/s?q=ML%20Engineer&l=Navi%20Mumbai");
  });
});

describe("template validation", () => {
  it("names unknown placeholders", () => {
    expect(
      findUnknownPlaceholders("https://x.com/{city}/{query}/{city}"),
    ).toEqual(["{city}"]);
    expect(templateError("https://x.com/{city}")).toBe(
      "Unknown placeholder: {city}",
    );
  });

  it("requires an absolute http(s) URL", () => {
    expect(templateError("/jobs/{query}")).toBe(
      "Must be an absolute http(s) URL",
    );
    expect(templateError("ftp://x.com/{query}")).toBe(
      "Must be an absolute http(s) URL",
    );
    expect(templateError("https://x.com/jobs?q={query}")).toBeNull();
  });
});

describe("normalizeList", () => {
  it("trims, drops blanks and dedupes ignoring case", () => {
    expect(
      normalizeList("java developer\n\n  Java Developer \r\nml engineer\n"),
    ).toEqual(["java developer", "ml engineer"]);
  });
});
