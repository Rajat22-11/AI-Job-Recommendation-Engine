import { describe, expect, it } from "vitest";
import {
  DEFAULT_THEME,
  parseTheme,
  resolveTheme,
  themeCookie,
  THEMES,
} from "./theme";

describe("parseTheme", () => {
  it("accepts every known preference", () => {
    for (const theme of THEMES) expect(parseTheme(theme)).toBe(theme);
  });

  it("falls back to dark when missing or invalid", () => {
    expect(DEFAULT_THEME).toBe("dark");
    expect(parseTheme(undefined)).toBe("dark");
    expect(parseTheme("")).toBe("dark");
    expect(parseTheme("blue")).toBe("dark");
    expect(parseTheme("DARK")).toBe("dark");
  });
});

describe("resolveTheme", () => {
  it("follows the OS only for system", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
});

describe("themeCookie", () => {
  it("is site-wide and lasts a year", () => {
    expect(themeCookie("light")).toBe(
      "theme=light; path=/; max-age=31536000; samesite=lax",
    );
  });
});
