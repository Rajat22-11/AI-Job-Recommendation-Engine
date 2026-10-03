import { createHash, createHmac, timingSafeEqual } from "node:crypto";

// Session token: base64url(JSON{exp}) + "." + base64url(HMAC-SHA256(secret, payload)).
// Pure functions so proxy.ts, Server Actions and tests share them.

export const SESSION_COOKIE = "session";
export const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;

function signature(secret: string, payload: string): Buffer {
  return createHmac("sha256", secret).update(payload).digest();
}

export function signSession(secret: string, now: number = Date.now()): string {
  const payload = Buffer.from(
    JSON.stringify({ exp: now + SESSION_TTL_MS }),
  ).toString("base64url");
  return `${payload}.${signature(secret, payload).toString("base64url")}`;
}

export function verifySession(
  secret: string,
  token: string | undefined,
  now: number = Date.now(),
): boolean {
  if (!token) return false;
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [payload, sig] = parts as [string, string];

  const expected = signature(secret, payload);
  const given = Buffer.from(sig, "base64url");
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) {
    return false;
  }

  try {
    const { exp } = JSON.parse(
      Buffer.from(payload, "base64url").toString("utf8"),
    ) as {
      exp?: unknown;
    };
    return typeof exp === "number" && exp > now;
  } catch {
    return false;
  }
}

/** Constant-time password check; hashing first hides length differences. */
export function passwordMatches(given: string, expected: string): boolean {
  const a = createHash("sha256").update(given).digest();
  const b = createHash("sha256").update(expected).digest();
  return timingSafeEqual(a, b);
}

/** Accept only same-origin relative paths as a post-login target. */
export function safeNextPath(next: unknown): string {
  if (typeof next !== "string") return "/";
  if (!next.startsWith("/") || next.startsWith("//") || next.includes("\\")) {
    return "/";
  }
  return next;
}
