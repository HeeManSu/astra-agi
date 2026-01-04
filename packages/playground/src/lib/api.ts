import type { Agent, Tool, Thread, Message, ServerInfo } from "./types";

// Get API base URL from injected config or default to same origin
function getApiBaseUrl(): string {
  const host = (window as { ASTRA_SERVER_HOST?: string }).ASTRA_SERVER_HOST;
  const port = (window as { ASTRA_SERVER_PORT?: string }).ASTRA_SERVER_PORT;
  const protocol = (window as { ASTRA_SERVER_PROTOCOL?: string })
    .ASTRA_SERVER_PROTOCOL;

  // If placeholders are still present (dev mode), use same origin
  if (host?.startsWith("%%") || !host) {
    return "";
  }

  return `${protocol}://${host}:${port}`;
}

const API_BASE = getApiBaseUrl();

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Server
export async function getServerInfo(): Promise<ServerInfo> {
  return fetchApi("/api/");
}

// Agents
export async function getAgents(): Promise<Agent[]> {
  return fetchApi("/api/agents");
}

export async function getAgent(agentId: string): Promise<Agent> {
  return fetchApi(`/api/agents/${agentId}`);
}

// Tools
export async function getTools(): Promise<Tool[]> {
  // This would need to be implemented in the backend
  // For now, return empty array
  return [];
}

// Threads
export async function getThreads(agentId: string): Promise<Thread[]> {
  return fetchApi(`/api/threads?agent_id=${agentId}`);
}

export async function getThread(threadId: string): Promise<Thread> {
  return fetchApi(`/api/threads/${threadId}`);
}

export async function createThread(agentId: string): Promise<Thread> {
  return fetchApi("/api/threads", {
    method: "POST",
    body: JSON.stringify({ agent_id: agentId }),
  });
}

// Messages
export async function getMessages(threadId: string): Promise<Message[]> {
  return fetchApi(`/api/threads/${threadId}/messages`);
}

export async function sendMessage(
  agentId: string,
  threadId: string,
  content: string
): Promise<Message> {
  return fetchApi(`/api/agents/${agentId}/chat`, {
    method: "POST",
    body: JSON.stringify({
      thread_id: threadId,
      message: content,
    }),
  });
}

// Streaming chat
export async function* streamChat(
  agentId: string,
  threadId: string,
  content: string
): AsyncGenerator<string, void, unknown> {
  const response = await fetch(`${API_BASE}/api/agents/${agentId}/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      thread_id: threadId,
      message: content,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") {
          return;
        }
        try {
          const parsed = JSON.parse(data);
          if (parsed.content) {
            yield parsed.content;
          }
        } catch {
          // Not JSON, yield as-is
          yield data;
        }
      }
    }
  }
}
