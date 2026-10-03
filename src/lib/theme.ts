// Theme preference. Safe to import from client and server code.

export const THEME_COOKIE = "theme";
export const THEMES = ["dark", "light", "system"] as const;
export type ThemePreference = (typeof THEMES)[number];
export const DEFAULT_THEME: ThemePreference = "dark";

export const THEME_LABELS: Record<ThemePreference, string> = {
  dark: "Dark",
  light: "Light",
  system: "System",
};

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

/** Unknown or missing values fall back to the dark default. */
export function parseTheme(value: string | undefined): ThemePreference {
  return (THEMES as readonly string[]).includes(value ?? "")
    ? (value as ThemePreference)
    : DEFAULT_THEME;
}

/** The theme actually painted. `system` follows the OS, `dark` until resolved. */
export function resolveTheme(
  preference: ThemePreference,
  systemPrefersDark: boolean,
): "dark" | "light" {
  if (preference === "system") return systemPrefersDark ? "dark" : "light";
  return preference;
}

export function themeCookie(preference: ThemePreference): string {
  return `${THEME_COOKIE}=${preference}; path=/; max-age=${ONE_YEAR_SECONDS}; samesite=lax`;
}

/**
 * Runs in <head> before first paint so a `system` preference never flashes the
 * wrong theme. Dark and Light are already correct in the server HTML.
 */
export const SYSTEM_THEME_SCRIPT = `(function(){try{var d=document.documentElement;if(d.getAttribute("data-theme-pref")==="system"){var t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";d.setAttribute("data-theme",t);d.style.colorScheme=t}}catch(e){}})()`;
