import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, verifySession } from "@/lib/auth/token";
import { getAuthConfig } from "@/lib/env";

// First line of defense; pages and Server Actions check the session again.
export function proxy(request: NextRequest) {
  const config = getAuthConfig();
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (config && verifySession(config.secret, token)) return NextResponse.next();

  const { pathname, search } = request.nextUrl;
  const loginUrl = new URL("/login", request.url);
  const next = pathname + search;
  if (next !== "/") loginUrl.searchParams.set("next", next);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|icon.svg|robots.txt|api/health|login).*)",
  ],
};
