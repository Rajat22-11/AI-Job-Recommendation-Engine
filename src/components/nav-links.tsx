"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Feed" },
  { href: "/tracker", label: "Tracker" },
  { href: "/sources", label: "Sources" },
  { href: "/runs", label: "Runs" },
  { href: "/settings", label: "Settings" },
] as const;

function isCurrent(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/jobs/");
  return pathname.startsWith(href);
}

export function NavLinks() {
  const pathname = usePathname();
  return (
    <ul className="flex gap-1">
      {links.map(({ href, label }) => {
        const current = isCurrent(pathname, href);
        return (
          <li key={href}>
            <Link
              href={href}
              aria-current={current ? "page" : undefined}
              className={`inline-flex tap items-center rounded-lg px-2.5 text-sm font-medium ${
                current
                  ? "bg-accent-soft text-accent"
                  : "text-text-muted hover:bg-muted hover:text-text"
              }`}
            >
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
