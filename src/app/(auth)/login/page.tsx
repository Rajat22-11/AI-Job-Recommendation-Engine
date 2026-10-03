import type { Metadata, Route } from "next";
import { redirect } from "next/navigation";
import { hasSession } from "@/lib/auth/session";
import { safeNextPath } from "@/lib/auth/token";
import { getAuthConfig } from "@/lib/env";
import { siteName } from "@/lib/site";
import { card } from "@/components/ui";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Log in" };

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { next } = await searchParams;
  const target = safeNextPath(next);
  if (await hasSession()) redirect(target as Route);

  const configured = getAuthConfig() !== null;

  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <div className={`${card} w-full max-w-sm p-6`}>
        <h1 className="mb-1 text-xl font-semibold">{siteName}</h1>
        <p className="mb-6 text-sm text-text-muted">
          Enter your password to continue.
        </p>
        {!configured && (
          <p
            role="alert"
            className="mb-4 rounded-lg bg-danger-soft p-3 text-sm text-danger"
          >
            Login isn&apos;t configured on the server. Set APP_PASSWORD and a
            SESSION_SECRET of at least 32 characters.
          </p>
        )}
        <LoginForm next={target} />
      </div>
    </main>
  );
}
