import { NextRequest, NextResponse } from "next/server";

const AGENT_API_BASE_URL = process.env.AGENT_API_BASE_URL || "http://localhost:8000";

async function proxyToBackend(req: NextRequest, sessionId: string) {
  const authHeader = req.headers.get("authorization");
  const headers: Record<string, string> = {};
  if (authHeader) {
    headers.Authorization = authHeader;
  }

  let body: string | undefined;
  if (req.method === "PATCH") {
    headers["Content-Type"] = "application/json";
    body = await req.text();
  }

  const upstream = await fetch(`${AGENT_API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: req.method,
    headers,
    body,
    cache: "no-store",
  });

  const responseBody = await upstream.text();
  return new NextResponse(responseBody, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") || "application/json",
    },
  });
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    const { sessionId } = await context.params;
    return await proxyToBackend(req, sessionId);
  } catch (error) {
    console.error("[api/sessions/:sessionId][GET] Proxy error:", error);
    return NextResponse.json({ error: "Failed to reach backend session endpoint" }, { status: 502 });
  }
}

export async function PATCH(
  req: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    const { sessionId } = await context.params;
    return await proxyToBackend(req, sessionId);
  } catch (error) {
    console.error("[api/sessions/:sessionId][PATCH] Proxy error:", error);
    return NextResponse.json({ error: "Failed to reach backend session endpoint" }, { status: 502 });
  }
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    const { sessionId } = await context.params;
    return await proxyToBackend(req, sessionId);
  } catch (error) {
    console.error("[api/sessions/:sessionId][DELETE] Proxy error:", error);
    return NextResponse.json({ error: "Failed to reach backend session endpoint" }, { status: 502 });
  }
}
