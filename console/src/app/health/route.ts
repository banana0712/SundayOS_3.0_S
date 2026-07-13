import { NextResponse } from "next/server";

const BACKEND = process.env.SUNDAY_BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const resp = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ ok: false, error: "backend_unreachable" }, { status: 502 });
  }
}
