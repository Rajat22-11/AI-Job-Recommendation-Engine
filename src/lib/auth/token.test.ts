import { describe, expect, it } from "vitest";
import {
  SESSION_TTL_MS,
  passwordMatches,
  safeNextPath,
  signSession,
  verifySession,
} from "./token";

const secret = "a".repeat(32);
const now = Date.parse("2026-10-03T12:00:00Z");

describe("session tokens", () => {
  it("accepts a freshly signed token", () => {
    expect(verifySession(secret, signSession(secret, now), now)).toBe(true);
  });

  it("rejects a tampered payload", () => {
    const [, sig] = signSession(secret, now).split(".");
    const forged = Buffer.from(
      JSON.stringify({ exp: now + 10 * SESSION_TTL_MS }),
    ).toString("base64url");
    expect(verifySession(secret, `${forged}.${sig}`, now)).toBe(false);
  });

  it("rejects malformed values", () => {
    for (const bad of [undefined, "", "abc", "a.b.c", "....", "x.y"]) {
      expect(verifySession(secret, bad, now)).toBe(false);
    }
  });

  it("rejects an expired token", () => {
    const token = signSession(secret, now);
    expect(verifySession(secret, token, now + SESSION_TTL_MS + 1)).toBe(false);
  });

  it("rejects tokens signed with a rotated secret", () => {
    const token = signSession(secret, now);
    expect(verifySession("b".repeat(32), token, now)).toBe(false);
  });
});

describe("passwordMatches", () => {
  it("compares exactly", () => {
    expect(passwordMatches("hunter2", "hunter2")).toBe(true);
    expect(passwordMatches("hunter", "hunter2")).toBe(false);
  });
});

describe("safeNextPath", () => {
  it("keeps relative paths with queries", () => {
    expect(safeNextPath("/?track=ml_ai&fit=4")).toBe("/?track=ml_ai&fit=4");
  });

  it("rejects external and protocol-relative targets", () => {
    for (const bad of [
      "https://evil.example",
      "//evil.example",
      "/\\evil.example",
      null,
    ]) {
      expect(safeNextPath(bad)).toBe("/");
    }
  });
});
