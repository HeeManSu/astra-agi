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

// ============================================================================
// Server
// ============================================================================

export async function getServerInfo(): Promise<ServerInfo> {
  return fetchApi("/api/");
}

// ============================================================================
// Agents
// ============================================================================

export async function getAgents(): Promise<Agent[]> {
  return fetchApi("/api/v1/agents");
}

export async function getAgent(agentName: string): Promise<Agent> {
  return fetchApi(`/api/v1/agents/${agentName}`);
}

// ============================================================================
// Tools
// ============================================================================

export async function getTools(): Promise<Tool[]> {
  return fetchApi("/api/v1/tools");
}

export async function getTool(toolName: string): Promise<Tool> {
  return fetchApi(`/api/v1/tools/${toolName}`);
}

// ============================================================================
// Threads
// ============================================================================

export async function getThreads(agentId: string): Promise<Thread[]> {
  return fetchApi(`/api/v1/agents/${agentId}/threads`);
}

export async function getThread(threadId: string): Promise<Thread> {
  return fetchApi(`/api/v1/threads/${threadId}`);
}

export async function createThread(
  agentId: string,
  title?: string,
  message?: string
): Promise<Thread> {
  const body: { title?: string; message?: string } = {};
  if (title) body.title = title;
  if (message) body.message = message;
  return fetchApi(`/api/v1/agents/${agentId}/threads`, {
    method: "POST",
    body: Object.keys(body).length > 0 ? JSON.stringify(body) : undefined,
  });
}

export async function deleteThread(threadId: string): Promise<void> {
  return fetchApi(`/api/v1/threads/${threadId}`, {
    method: "DELETE",
  });
}

// ============================================================================
// Messages
// ============================================================================

export async function getMessages(threadId: string): Promise<Message[]> {
  return fetchApi(`/api/v1/threads/${threadId}/messages`);
}

export async function addMessage(
  threadId: string,
  content: string
): Promise<Message> {
  return fetchApi(`/api/v1/threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

// ============================================================================
// Generate (non-streaming)
// ============================================================================

export interface GenerateRequest {
  message: string;
  thread_id?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface GenerateResponse {
  content: string;
  thread_id?: string;
}

export async function generateAgentResponse(
  agentId: string,
  request: GenerateRequest
): Promise<GenerateResponse> {
  return fetchApi(`/api/v1/agents/${agentId}/generate`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

// ============================================================================
// Stream (streaming chat)
// ============================================================================

export async function* streamAgentResponse(
  agentId: string,
  request: GenerateRequest
): AsyncGenerator<
  { type: "thinking" | "token" | "done" | "error"; data: unknown },
  void,
  unknown
> {
  const response = await fetch(`${API_BASE}/api/v1/agents/${agentId}/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent: string | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || ""; // Keep incomplete line in buffer

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ") && currentEvent) {
        const dataStr = line.slice(6);
        try {
          const data = JSON.parse(dataStr);
          yield {
            type: currentEvent as "thinking" | "token" | "done" | "error",
            data,
          };
          currentEvent = null;
        } catch (e) {
          if (e instanceof SyntaxError) {
            continue;
          }
          throw e;
        }
      } else if (line.trim() === "") {
        // Empty line resets event
        currentEvent = null;
      }
    }
  }
}

// ============================================================================
// Auth
// ============================================================================

export interface SessionStatus {
  authenticated: boolean;
  email: string | null;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  email?: string;
}

// Get CSRF token from cookie
function getCsrfToken(): string | null {
  const match = document.cookie.match(/astra_csrf=([^;]+)/);
  return match ? match[1] : null;
}

// Fetch with credentials and CSRF token
async function fetchWithAuth<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  // Add CSRF token for mutating requests
  if (
    options?.method &&
    ["POST", "PUT", "DELETE", "PATCH"].includes(options.method)
  ) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function getSession(): Promise<SessionStatus> {
  return fetchWithAuth("/auth/session");
}

export async function needsSignup(): Promise<{ needs_signup: boolean }> {
  // This is a public endpoint, doesn't need auth
  return fetchApi("/auth/needs-signup");
}

export async function login(
  email: string,
  password: string
): Promise<AuthResponse> {
  return fetchWithAuth("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function signup(
  email: string,
  password: string
): Promise<AuthResponse> {
  return fetchWithAuth("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<AuthResponse> {
  return fetchWithAuth("/auth/logout", {
    method: "POST",
  });
}
