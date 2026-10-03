import "server-only";
import { cookies } from "next/headers";
import { parseTheme, THEME_COOKIE, type ThemePreference } from "@/lib/theme";

export async function readTheme(): Promise<ThemePreference> {
  return parseTheme((await cookies()).get(THEME_COOKIE)?.value);
}
