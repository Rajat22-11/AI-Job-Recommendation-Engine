// Render health check. Deliberately avoids the database.
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ ok: true });
}
