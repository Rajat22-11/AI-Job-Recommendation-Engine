// Search URL templates used by the scraper, plus list normalization for settings.

export const TEMPLATE_PLACEHOLDERS = [
  "query",
  "query_slug",
  "location",
] as const;

export const PLACEHOLDER_HELP: Record<
  (typeof TEMPLATE_PLACEHOLDERS)[number],
  string
> = {
  query: "the keyword, URL-encoded (Java Developer → Java%20Developer)",
  query_slug: "the keyword lowercased with spaces as hyphens (java-developer)",
  location: "the location, URL-encoded",
};

export function querySlug(query: string): string {
  return query.trim().toLowerCase().replace(/\s+/g, "-");
}

export function expandTemplate(
  template: string,
  { query, location }: { query: string; location: string },
): string {
  return template
    .replaceAll("{query_slug}", querySlug(query))
    .replaceAll("{query}", encodeURIComponent(query))
    .replaceAll("{location}", encodeURIComponent(location));
}

/** Placeholders other than the supported three, e.g. ["{city}"]. */
export function findUnknownPlaceholders(template: string): string[] {
  const unknown = new Set<string>();
  for (const match of template.matchAll(/\{([^{}]*)\}/g)) {
    const name = match[1] ?? "";
    if (!(TEMPLATE_PLACEHOLDERS as readonly string[]).includes(name))
      unknown.add(match[0]);
  }
  return [...unknown];
}

export function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

/** Error message for a template, or null when it is valid. */
export function templateError(template: string): string | null {
  const unknown = findUnknownPlaceholders(template);
  if (unknown.length > 0) {
    return `Unknown placeholder${unknown.length > 1 ? "s" : ""}: ${unknown.join(", ")}`;
  }
  const sample = expandTemplate(template, {
    query: "software engineer",
    location: "Pune",
  });
  return isHttpUrl(sample) ? null : "Must be an absolute http(s) URL";
}

/** One entry per line: trimmed, blanks dropped, duplicates (ignoring case) removed. */
export function normalizeList(text: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const line of text.split(/\r?\n/)) {
    const value = line.trim();
    const key = value.toLowerCase();
    if (value && !seen.has(key)) {
      seen.add(key);
      result.push(value);
    }
  }
  return result;
}
