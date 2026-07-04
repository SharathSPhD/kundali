// Legacy proxy kept for backward compatibility. New code calls /api/py/*
// directly (routed to the Python function by vercel.json in production and
// by next.config.mjs rewrites in dev). This handler forwards /api/engine/*
// to the same engine, attaching the Supabase access token server-side.

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

function apiBase(req: NextRequest): string {
  // Explicit override first; otherwise same-origin Python function.
  return process.env.API_BASE_URL
    ? `${process.env.API_BASE_URL.replace(/\/$/, "")}/api`
    : `${req.nextUrl.origin}/api/py`;
}

async function proxy(
  req: NextRequest,
  params: { path: string[] },
  method: "GET" | "POST"
): Promise<NextResponse> {
  const path = (params.path ?? []).join("/");
  const target = `${apiBase(req)}/${path}${req.nextUrl.search}`;

  const headers: Record<string, string> = {
    "Content-Type": req.headers.get("content-type") ?? "application/json",
  };

  const supabase = createClient();
  if (supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) {
      headers["Authorization"] = `Bearer ${session.access_token}`;
    }
  }

  const init: RequestInit = { method, headers, cache: "no-store" };
  if (method === "POST") {
    init.body = await req.text();
  }

  try {
    const upstream = await fetch(target, init);
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (err) {
    return NextResponse.json(
      {
        error: "engine_unreachable",
        detail: `Could not reach the calculation engine at ${apiBase(req)}.`,
      },
      { status: 502 }
    );
  }
}

export async function GET(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params, "GET");
}

export async function POST(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxy(req, params, "POST");
}
