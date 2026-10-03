import "server-only";
import { cache } from "react";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { getSupabaseConfig } from "@/lib/env";
import type { Database } from "./database.types";

let client: SupabaseClient<Database> | undefined;

/** Service-role client. Created lazily so `next build` never needs credentials. */
export function db(): SupabaseClient<Database> {
  if (!client) {
    const { url, serviceRoleKey } = getSupabaseConfig();
    client = createClient<Database>(url, serviceRoleKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
  }
  return client;
}

/** Source id → display name, loaded once per request. */
export const getSourceNames = cache(async (): Promise<Map<string, string>> => {
  const { data, error } = await db().from("sources").select("id, name");
  if (error) throw error;
  return new Map(data.map((s) => [s.id, s.name]));
});

export function sourceName(names: Map<string, string>, id: string): string {
  return names.get(id) ?? id;
}
