import type { Metadata, Viewport } from "next";
import { siteName } from "@/lib/site";
import { resolveTheme, SYSTEM_THEME_SCRIPT } from "@/lib/theme";
import { readTheme } from "@/lib/theme-server";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: siteName,
    template: `%s | ${siteName}`,
  },
  // Private app: never indexed.
  robots: { index: false, follow: false },
};

// Page background per theme (the canvas token), for the mobile browser toolbar.
const THEME_COLOR = { dark: "#0d1117", light: "#f6f7f9" } as const;

export async function generateViewport(): Promise<Viewport> {
  const preference = await readTheme();
  if (preference === "system") {
    return {
      colorScheme: "light dark",
      themeColor: [
        { media: "(prefers-color-scheme: dark)", color: THEME_COLOR.dark },
        { media: "(prefers-color-scheme: light)", color: THEME_COLOR.light },
      ],
    };
  }
  return { colorScheme: preference, themeColor: THEME_COLOR[preference] };
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const preference = await readTheme();
  // For `system` the head script corrects this before first paint.
  const theme = resolveTheme(preference, true);

  return (
    // The head script may change data-theme before React hydrates.
    <html
      lang="en"
      data-theme={theme}
      data-theme-pref={preference}
      style={{ colorScheme: theme }}
      suppressHydrationWarning
    >
      <head>
        {preference === "system" && (
          <script dangerouslySetInnerHTML={{ __html: SYSTEM_THEME_SCRIPT }} />
        )}
      </head>
      <body>{children}</body>
    </html>
  );
}
