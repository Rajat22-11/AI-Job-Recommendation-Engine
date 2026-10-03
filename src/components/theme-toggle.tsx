"use client";

import { useEffect, useState } from "react";
import {
  resolveTheme,
  THEME_LABELS,
  themeCookie,
  THEMES,
  type ThemePreference,
} from "@/lib/theme";

const DARK_QUERY = "(prefers-color-scheme: dark)";

function paint(preference: ThemePreference) {
  const theme = resolveTheme(preference, matchMedia(DARK_QUERY).matches);
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  root.setAttribute("data-theme-pref", preference);
  root.style.colorScheme = theme;
}

/** Dark / Light / System choice, saved in a cookie the server reads. */
export function ThemeToggle({ initial }: { initial: ThemePreference }) {
  const [preference, setPreference] = useState(initial);

  // While on System, follow the OS if it changes with the app open.
  useEffect(() => {
    if (preference !== "system") return;
    const media = matchMedia(DARK_QUERY);
    const onChange = () => paint("system");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [preference]);

  function choose(next: ThemePreference) {
    setPreference(next);
    document.cookie = themeCookie(next);
    paint(next);
  }

  return (
    <div>
      <label htmlFor="theme" className="sr-only">
        Theme
      </label>
      <select
        id="theme"
        value={preference}
        onChange={(e) => choose(e.target.value as ThemePreference)}
        className="tap rounded-lg border border-border-strong bg-surface px-2 text-sm text-text"
      >
        {THEMES.map((theme) => (
          <option key={theme} value={theme}>
            {THEME_LABELS[theme]}
          </option>
        ))}
      </select>
    </div>
  );
}
