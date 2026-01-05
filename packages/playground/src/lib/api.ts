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
  return fetchApi("/api/agents");
}

export async function getAgent(agentName: string): Promise<Agent> {
  return fetchApi(`/api/agents/${agentName}`);
}

// ============================================================================
// Tools
// ============================================================================

export async function getTools(): Promise<Tool[]> {
  return fetchApi("/api/tools");
}

export async function getTool(toolName: string): Promise<Tool> {
  return fetchApi(`/api/tools/${toolName}`);
}

// ============================================================================
// Threads
// ============================================================================

export async function getThreads(agentName: string): Promise<Thread[]> {
  return fetchApi(`/api/agents/${agentName}/threads`);
}

export async function getThread(threadId: string): Promise<Thread> {
  return fetchApi(`/api/threads/${threadId}`);
}

export async function createThread(agentName: string): Promise<Thread> {
  return fetchApi(`/api/agents/${agentName}/threads`, {
    method: "POST",
  });
}

export async function deleteThread(threadId: string): Promise<void> {
  return fetchApi(`/api/threads/${threadId}`, {
    method: "DELETE",
  });
}

// ============================================================================
// Messages
// ============================================================================

export async function getMessages(threadId: string): Promise<Message[]> {
  return fetchApi(`/api/threads/${threadId}/messages`);
}

export async function addMessage(
  threadId: string,
  content: string
): Promise<Message> {
  return fetchApi(`/api/threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

// ============================================================================
// Generate (streaming chat)
// ============================================================================

export async function* streamGenerate(
  threadId: string,
  message: string
): AsyncGenerator<string, void, unknown> {
  const response = await fetch(`${API_BASE}/api/threads/${threadId}/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
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
          if (parsed.error) {
            throw new Error(parsed.error);
          }
        } catch (e) {
          if (e instanceof SyntaxError) {
            // Not JSON, skip
            continue;
          }
          throw e;
        }
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
  return fetchWithAuth("/auth/needs-signup");
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
