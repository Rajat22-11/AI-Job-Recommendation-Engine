// Server-side environment access. None of these variables use the NEXT_PUBLIC_
// prefix, so Next.js never inlines them into client bundles. This module stays
// free of `server-only` because proxy.ts and unit tests import it too.

const MIN_SECRET_LENGTH = 32;

export interface AuthConfig {
  password: string;
  secret: string;
}

/** Auth settings, or null when they are missing or too weak (fail closed). */
export function getAuthConfig(): AuthConfig | null {
  const password = process.env.APP_PASSWORD;
  const secret = process.env.SESSION_SECRET;
  if (!password || !secret || secret.length < MIN_SECRET_LENGTH) return null;
  return { password, secret };
}

export interface SupabaseConfig {
  url: string;
  serviceRoleKey: string;
}

export function getSupabaseConfig(): SupabaseConfig {
  const url = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceRoleKey) {
    throw new Error(
      "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set (see .env.example).",
    );
  }
  return { url, serviceRoleKey };
}
