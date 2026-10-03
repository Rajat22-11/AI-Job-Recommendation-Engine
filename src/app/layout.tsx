import type { Metadata, Viewport } from "next";
import { siteName } from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: siteName,
    template: `%s | ${siteName}`,
  },
  // Private app: never indexed.
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
