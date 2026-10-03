import Link from "next/link";
import { Suspense } from "react";
import { logout } from "@/lib/actions/auth";
import { requireSession } from "@/lib/auth/session";
import { siteName } from "@/lib/site";
import { LoginBanner } from "@/components/login-banner";
import { NavLinks } from "@/components/nav-links";
import { ToastProvider } from "@/components/toast";
import { btnGhost } from "@/components/ui";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  await requireSession();

  return (
    <>
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 px-4 py-1">
          <Link
            href="/"
            className="mr-auto inline-flex tap items-center font-semibold"
          >
            {siteName}
          </Link>
          <nav
            aria-label="Main"
            className="order-last w-full sm:order-none sm:w-auto"
          >
            <NavLinks />
          </nav>
          <form action={logout}>
            <button type="submit" className={btnGhost}>
              Log out
            </button>
          </form>
        </div>
      </header>
      <Suspense fallback={null}>
        <LoginBanner />
      </Suspense>
      <ToastProvider>
        <main className="mx-auto max-w-6xl px-4 py-4 pb-24">{children}</main>
      </ToastProvider>
    </>
  );
}
