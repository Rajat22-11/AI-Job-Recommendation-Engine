import Link from "next/link";
import { btnSecondary } from "@/components/ui";

export function NotFoundMessage() {
  return (
    <div className="py-16 text-center">
      <h1 className="mb-2 text-xl font-semibold">Page not found</h1>
      <p className="mb-6 text-text-muted">
        This page or job doesn&apos;t exist. It may have been removed.
      </p>
      <Link href="/" className={btnSecondary}>
        Back to the feed
      </Link>
    </div>
  );
}
