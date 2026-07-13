import { NextRequest, NextResponse } from "next/server";

// Universal server-side proxy — all /api/* calls from the browser go through here.
// The API key stays server-side, never reaches the browser.
// Configure via .env.local:
//   SUNDAY_BACKEND_URL (default http://localhost:8000)
//   SUNDAY_API_KEY     (default dev-key)
const BACKEND = process.env.SUNDAY_BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.SUNDAY_API_KEY ?? "dev-key";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  try {
    const url = `${BACKEND}/api/${path.join("/")}?${req.nextUrl.searchParams.toString()}`;
    const resp = await fetch(url, {
      headers: { "X-API-Key": API_KEY },
      cache: "no-store",
    });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "backend_unreachable" }, { status: 502 });
  }
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad_request" }, { status: 400 });
  }
  try {
    const url = `${BACKEND}/api/${path.join("/")}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "backend_unreachable" }, { status: 502 });
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad_request" }, { status: 400 });
  }
  try {
    const url = `${BACKEND}/api/${path.join("/")}`;
    const resp = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "backend_unreachable" }, { status: 502 });
  }
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  try {
    const url = `${BACKEND}/api/${path.join("/")}`;
    const resp = await fetch(url, {
      method: "DELETE",
      headers: { "X-API-Key": API_KEY },
      cache: "no-store",
    });
    const data = await resp.json().catch(() => ({}));
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json({ error: "backend_unreachable" }, { status: 502 });
  }
}
