/**
 * Imperative Astra Runtime client. Only endpoints that can't go through RTK
 * Query live here:
 *   - `/auth/token` and `/health` — bootstrap the connect flow
 *   - `GET /agents`, `GET /teams` — fired during the connect flow before the
 *     store knows the apiKey, so we call them directly with the freshly minted
 *     token rather than through the cache
 *   - `/agents/:id/invoke|stream`, `/teams/:id/invoke|stream` — streaming, not
 *     supported by RTK Query
 *   - `POST /threads` — fired from `useChatStream` when the first message of
 *     an ad-hoc chat needs to spawn a thread (one-shot, not subscription)
 *
 * Everything else (list threads, list tools, list traces, mutations that
 * affect those caches) lives in `@/api/rtkApi.ts`.
 */

import { z } from "zod";
import type {
  Agent,
  Team,
  Thread,
  ThreadCreate,
  TokenResponse,
  InvokeResponse,
} from "@/types/api";
import type { StreamCallbacks } from "@/types/sse";
import {
  AgentSchema,
  TeamSchema,
  ThreadSchema,
  TokenResponseSchema,
  InvokeResponseSchema,
} from "@/api/schemas";
import { consumeSseStream } from "@/api/sse";

function trimTrailingSlash(url: string): string {
  return url.replace(/\/$/, "");
}

function createHeaders(apiKey: string): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
  return headers;
}

async function parseJson<T>(
  response: Response,
  schema: z.ZodType<T>,
  context: string,
): Promise<T> {
  if (!response.ok) {
    throw new Error(`${context}: ${response.statusText}`);
  }
  const json: unknown = await response.json();
  return schema.parse(json);
}

interface RunBody {
  message: string;
  thread_id?: string;
}

function buildRunBody(message: string, threadId?: string | null): RunBody {
  const body: RunBody = { message };
  if (threadId) body.thread_id = threadId;
  return body;
}

// ---------- Auth + health -------------------------------------------

export async function getAuthToken(serverUrl: string): Promise<TokenResponse> {
  const response = await fetch(`${trimTrailingSlash(serverUrl)}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return parseJson(response, TokenResponseSchema, "Failed to get token");
}

export async function checkHealth(
  serverUrl: string,
  apiKey: string,
): Promise<boolean> {
  const response = await fetch(`${trimTrailingSlash(serverUrl)}/health`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });
  return response.ok;
}

// ---------- Agents / Teams (connect-flow only) ----------------------

export async function getAgents(
  serverUrl: string,
  apiKey: string,
): Promise<Agent[]> {
  const response = await fetch(`${trimTrailingSlash(serverUrl)}/agents`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });
  return parseJson(
    response,
    z.array(AgentSchema),
    "Failed to fetch agents",
  );
}

export async function getTeams(
  serverUrl: string,
  apiKey: string,
): Promise<Team[]> {
  const response = await fetch(`${trimTrailingSlash(serverUrl)}/teams`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });
  return parseJson(response, z.array(TeamSchema), "Failed to fetch teams");
}

// ---------- Invoke + stream -----------------------------------------

export async function runAgent(
  serverUrl: string,
  apiKey: string,
  agentId: string,
  message: string,
  threadId?: string | null,
): Promise<InvokeResponse> {
  const response = await fetch(
    `${trimTrailingSlash(serverUrl)}/agents/${agentId}/invoke`,
    {
      method: "POST",
      headers: createHeaders(apiKey),
      body: JSON.stringify(buildRunBody(message, threadId)),
    },
  );
  return parseJson(response, InvokeResponseSchema, "Failed to run agent");
}

export async function streamAgent(
  serverUrl: string,
  apiKey: string,
  agentId: string,
  message: string,
  onChunk: StreamCallbacks["onChunk"],
  onDone: StreamCallbacks["onDone"],
  onError: StreamCallbacks["onError"],
  threadId?: string | null,
): Promise<void> {
  try {
    const response = await fetch(
      `${trimTrailingSlash(serverUrl)}/agents/${agentId}/stream`,
      {
        method: "POST",
        headers: createHeaders(apiKey),
        body: JSON.stringify(buildRunBody(message, threadId)),
      },
    );
    if (!response.ok) {
      throw new Error(`Failed to stream agent: ${response.statusText}`);
    }
    await consumeSseStream(response, { onChunk, onDone, onError });
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

export async function runTeam(
  serverUrl: string,
  apiKey: string,
  teamId: string,
  message: string,
  threadId?: string | null,
): Promise<InvokeResponse> {
  const response = await fetch(
    `${trimTrailingSlash(serverUrl)}/teams/${teamId}/invoke`,
    {
      method: "POST",
      headers: createHeaders(apiKey),
      body: JSON.stringify(buildRunBody(message, threadId)),
    },
  );
  return parseJson(response, InvokeResponseSchema, "Failed to run team");
}

export async function streamTeam(
  serverUrl: string,
  apiKey: string,
  teamId: string,
  message: string,
  onChunk: StreamCallbacks["onChunk"],
  onDone: StreamCallbacks["onDone"],
  onError: StreamCallbacks["onError"],
  threadId?: string | null,
): Promise<void> {
  try {
    const response = await fetch(
      `${trimTrailingSlash(serverUrl)}/teams/${teamId}/stream`,
      {
        method: "POST",
        headers: createHeaders(apiKey),
        body: JSON.stringify(buildRunBody(message, threadId)),
      },
    );
    if (!response.ok) {
      throw new Error(`Failed to stream team: ${response.statusText}`);
    }
    await consumeSseStream(response, { onChunk, onDone, onError });
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

// ---------- Threads (fire-and-forget creation) -----------------------

export async function createThread(
  serverUrl: string,
  apiKey: string,
  data: ThreadCreate,
): Promise<Thread> {
  const response = await fetch(`${trimTrailingSlash(serverUrl)}/threads`, {
    method: "POST",
    headers: createHeaders(apiKey),
    body: JSON.stringify(data),
  });
  return parseJson(response, ThreadSchema, "Failed to create thread");
}
