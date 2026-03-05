import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// API URL Configuration - uses environment variables with fallbacks
const AGENT_API_BASE_URL = process.env.AGENT_API_BASE_URL || "http://localhost:8000";
const LOGISTICS_AGENT_URL = process.env.AGENT_LOGISTICS_URL || `${AGENT_API_BASE_URL}/logistics`;

// 1. You can use any service adapter here for multi-agent support. We use
//    the empty adapter since we're only using one agent.
const serviceAdapter = new ExperimentalEmptyAdapter();

// Create a function to build the runtime with the auth header
function createRuntime(authHeader: string | null) {
  const agentHeaders: Record<string, string> = {};
  if (authHeader) {
    agentHeaders["Authorization"] = authHeader;
  }

  return new CopilotRuntime({
    agents: {
      "logistics_agent": new HttpAgent({
        url: LOGISTICS_AGENT_URL,
        headers: agentHeaders,
      }),
    }
  });
}

// 2. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Get the Authorization header from the request
  const authHeader = req.headers.get("authorization");

  // Clone the request and remove the Authorization header to prevent duplication
  // CopilotKit might be forwarding it separately
  const headers = new Headers(req.headers);
  headers.delete("authorization");

  // Create a new request without the auth header in the HTTP headers
  // We'll pass it directly to the HttpAgent
  const modifiedReq = new NextRequest(req.url, {
    method: req.method,
    headers: headers,
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
};
