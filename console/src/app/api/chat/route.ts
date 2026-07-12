import { NextRequest, NextResponse } from "next/server";

// Server-side proxy to the Sunday backend. The API key stays here (server),
// never reaches the browser. Configure via env:
//   SUNDAY_BACKEND_URL (default http://localhost:8000)
//   SUNDAY_API_KEY     (default dev-key — matches the backend's default)
const BACKEND = process.env.SUNDAY_BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.SUNDAY_API_KEY ?? "dev-key";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad_request" }, { status: 400 });
  }

  try {
    const resp = await fetch(`${BACKEND}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify(body),
      // don't cache chat
      cache: "no-store",
    });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch {
    // backend unreachable
    return NextResponse.json({ error: "backend_unreachable" }, { status: 502 });
  }
}

export async function GET() {
  // health passthrough for the connection indicator
  try {
    const resp = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json({ ok: resp.ok, ...data }, { status: resp.ok ? 200 : 502 });
  } catch {
    return NextResponse.json({ ok: false, error: "backend_unreachable" }, { status: 502 });
  }
}
