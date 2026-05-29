import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest, NextResponse } from "next/server";

const AGENT_API_BASE_URL = process.env.AGENT_API_BASE_URL || "http://localhost:8000";
const LOGISTICS_AGENT_URL =
  process.env.AGENT_LOGISTICS_URL || `${AGENT_API_BASE_URL}/logistics`;

const serviceAdapter = new ExperimentalEmptyAdapter();

function createRuntime(authHeader: string | null) {
  const agentHeaders: Record<string, string> = {};
  if (authHeader) {
    agentHeaders["Authorization"] = authHeader;
  }

  return new CopilotRuntime({
    agents: {
      logistics_agent: new HttpAgent({
        url: LOGISTICS_AGENT_URL,
        headers: agentHeaders,
      }),
    },
  });
}

async function handleCopilotRequest(req: NextRequest) {
  const path = req.nextUrl.pathname;

  // CopilotKit requests thread metadata via GET /api/copilotkit/threads.
  // We use external Foundry conversation IDs, so we return an empty list.
  if (req.method === "GET" && path.endsWith("/threads")) {
    return NextResponse.json({ threads: [] });
  }

  const authHeader = req.headers.get("authorization");
  const headers = new Headers(req.headers);
  headers.delete("authorization");

  const modifiedReq = new NextRequest(req.url, {
    method: req.method,
    headers,
    body: req.body,
    duplex: "half" as const,
  });

  const runtime = createRuntime(authHeader);
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(modifiedReq);
}

export const GET = async (req: NextRequest) => handleCopilotRequest(req);
export const POST = async (req: NextRequest) => handleCopilotRequest(req);