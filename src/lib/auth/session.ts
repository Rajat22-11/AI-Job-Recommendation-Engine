import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getAuthConfig } from "@/lib/env";
import {
  SESSION_COOKIE,
  SESSION_TTL_MS,
  signSession,
  verifySession,
} from "./token";

export async function hasSession(): Promise<boolean> {
  // Read cookies first: it marks every gated page as dynamic, so a build
  // without auth config can never prerender a static redirect.
  const jar = await cookies();
  const config = getAuthConfig();
  if (!config) return false;
  return verifySession(config.secret, jar.get(SESSION_COOKIE)?.value);
}

/** For pages: redirect to login when there is no valid session. */
export async function requireSession(): Promise<void> {
  if (!(await hasSession())) redirect("/login");
}

/** For Server Actions: refuse to run without a valid session. */
export async function assertSession(): Promise<void> {
  if (!(await hasSession())) throw new Error("Not authenticated");
}

export async function startSession(secret: string): Promise<void> {
  const jar = await cookies();
  jar.set(SESSION_COOKIE, signSession(secret), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_TTL_MS / 1000,
  });
}

export async function endSession(): Promise<void> {
  const jar = await cookies();
  jar.delete(SESSION_COOKIE);
}
