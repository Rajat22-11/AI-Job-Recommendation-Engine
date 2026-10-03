import Link from "next/link";
import { getLoginAlerts } from "@/lib/db/queries/sources";

// Never allowed to break a page: any failure renders nothing.
export async function LoginBanner() {
  let alerts: { id: string; name: string }[];
  try {
    alerts = await getLoginAlerts();
  } catch (error) {
    console.error("Login banner unavailable", error);
    return null;
  }
  if (alerts.length === 0) return null;

  return (
    <div role="alert" className="border-b border-warning/30 bg-warning-soft">
      <ul className="mx-auto max-w-6xl space-y-1 px-4 py-2 text-sm text-warning">
        {alerts.map((source) => (
          <li key={source.id}>
            <Link
              href="/sources"
              className="font-medium underline underline-offset-2"
            >
              Log in to {source.name} in Chrome before the next run.
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
