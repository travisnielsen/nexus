import { NextRequest, NextResponse } from "next/server";

const AGENT_API_BASE_URL = process.env.AGENT_API_BASE_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    const authHeader = req.headers.get("authorization");
    const headers: Record<string, string> = {};
    if (authHeader) {
      headers.Authorization = authHeader;
    }

    const upstream = await fetch(`${AGENT_API_BASE_URL}/api/sessions`, {
      method: "GET",
      headers,
      cache: "no-store",
    });

    const bodyText = await upstream.text();
    return new NextResponse(bodyText, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    console.error("[api/sessions] Proxy error:", error);
    return NextResponse.json({ error: "Failed to reach backend sessions endpoint" }, { status: 502 });
  }
}
