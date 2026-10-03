// Pure rules for adding and editing sources from Settings.

import type { TablesUpdate } from "@/lib/db/database.types";

const MAX_ID_LENGTH = 40;
const MIN_ID_LENGTH = 2;
const MAX_SUFFIX = 9;

/** Lowercase ASCII letters and digits, other runs turned into "-". */
function slugify(text: string, maxLength: number): string {
  return text
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+/, "")
    .slice(0, maxLength)
    .replace(/-+$/, "");
}

/** The site part of a URL used to tell sources apart: host without "www.". */
export function siteHost(url: string): string | null {
  try {
    return new URL(url).host.toLowerCase().replace(/^www\./, "");
  } catch {
    return null;
  }
}

/**
 * Id for a new source: from the name, or from the base URL's host when the
 * name has too few letters or digits. A taken id gets "-2" … "-9".
 * Returns null when every candidate is taken or nothing usable is left.
 */
export function deriveSourceId(
  name: string,
  baseUrl: string,
  takenIds: Iterable<string>,
): string | null {
  const taken = new Set(takenIds);
  const fromName = (max: number) => slugify(name, max);
  const fromHost = (max: number) => slugify(siteHost(baseUrl) ?? "", max);
  const base = (max: number) => {
    const id = fromName(max);
    return id.length >= MIN_ID_LENGTH ? id : fromHost(max);
  };

  const plain = base(MAX_ID_LENGTH);
  if (plain.length < MIN_ID_LENGTH) return null;
  if (!taken.has(plain)) return plain;

  for (let n = 2; n <= MAX_SUFFIX; n++) {
    const suffix = `-${n}`;
    const id = `${base(MAX_ID_LENGTH - suffix.length)}${suffix}`;
    if (!taken.has(id)) return id;
  }
  return null;
}

/** An existing source on the same site as `baseUrl`, if any. */
export function sameSiteSource<T extends { base_url: string }>(
  baseUrl: string,
  sources: readonly T[],
): T | null {
  const host = siteHost(baseUrl);
  if (!host) return null;
  return sources.find((s) => siteHost(s.base_url) === host) ?? null;
}

export interface PlainSourceFields {
  name: string;
  base_url: string;
  requires_login: boolean;
  enabled: boolean;
  notes: string | null;
}

export interface SourceOverride {
  access_method: string;
  search_url_template: string;
  /** Values the form was loaded with. */
  orig_access_method: string;
  orig_search_url_template: string;
}

/**
 * Update payload for an edited source. Only override values that differ from
 * what the form was loaded with are written, so a template the trigger
 * learned meanwhile is never overwritten by a stale form.
 */
export function sourceUpdatePayload(
  plain: PlainSourceFields,
  override: SourceOverride,
): TablesUpdate<"sources"> {
  const payload: TablesUpdate<"sources"> = { ...plain };

  const method = override.access_method.trim();
  if (method && method !== override.orig_access_method.trim()) {
    payload.access_method = method;
  }

  const template = override.search_url_template.trim();
  if (template !== override.orig_search_url_template.trim()) {
    Object.assign(payload, {
      search_url_template: template || null,
      // A cleared template is learned again by the trigger.
      template_origin: template ? "manual" : null,
      template_status: "unverified",
      template_verified_at: null,
    });
  }
  return payload;
}

/** Whether the override changes the template, so it needs validating. */
export function templateChanged(override: SourceOverride): boolean {
  return (
    override.search_url_template.trim() !==
    override.orig_search_url_template.trim()
  );
}
