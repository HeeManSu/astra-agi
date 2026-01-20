/**
 * Astra Runtime API Client
 *
 * Handles all API calls to the Astra Runtime server.
 */

// Helper to create headers with optional auth
const createHeaders = (apiKey) => {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  return headers;
};

/**
 * Get auth token from server
 */
export const getAuthToken = async (serverUrl) => {
  const response = await fetch(`${serverUrl}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Failed to get token: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Check if server is reachable
 */
export const checkHealth = async (serverUrl, apiKey) => {
  const response = await fetch(`${serverUrl}/health`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });
  return response.ok;
};

/**
 * Get list of agents
 */
export const getAgents = async (serverUrl, apiKey) => {
  const response = await fetch(`${serverUrl}/agents`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Get list of teams
 */
export const getTeams = async (serverUrl, apiKey) => {
  const response = await fetch(`${serverUrl}/teams`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch teams: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Run an agent (non-streaming)
 */
export const runAgent = async (
  serverUrl,
  apiKey,
  agentId,
  message,
  threadId = null,
) => {
  const body = { message };
  if (threadId) body.thread_id = threadId;

  const response = await fetch(`${serverUrl}/agents/${agentId}/invoke`, {
    method: "POST",
    headers: createHeaders(apiKey),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Failed to run agent: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Run an agent with streaming (SSE)
 */
export const streamAgent = async (
  serverUrl,
  apiKey,
  agentId,
  message,
  onChunk,
  onDone,
  onError,
  threadId = null,
) => {
  try {
    const body = { message };
    if (threadId) body.thread_id = threadId;

    const response = await fetch(`${serverUrl}/agents/${agentId}/stream`, {
      method: "POST",
      headers: createHeaders(apiKey),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Failed to stream agent: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onDone();
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process SSE events
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();

          if (data === "[DONE]") {
            onDone();
            return;
          }

          try {
            const event = JSON.parse(data);
            onChunk(event);
          } catch (e) {
            // Not JSON, might be raw text
            if (data) {
              onChunk({ type: "content", content: data });
            }
          }
        }
      }
    }
  } catch (error) {
    onError(error);
  }
};

/**
 * Run a team (non-streaming)
 */
export const runTeam = async (
  serverUrl,
  apiKey,
  teamId,
  message,
  threadId = null,
) => {
  const body = { message };
  if (threadId) body.thread_id = threadId;

  const response = await fetch(`${serverUrl}/teams/${teamId}/invoke`, {
    method: "POST",
    headers: createHeaders(apiKey),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Failed to run team: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Run a team with streaming (SSE)
 */
export const streamTeam = async (
  serverUrl,
  apiKey,
  teamId,
  message,
  onChunk,
  onDone,
  onError,
  threadId = null,
) => {
  try {
    const body = { message };
    if (threadId) body.thread_id = threadId;

    const response = await fetch(`${serverUrl}/teams/${teamId}/stream`, {
      method: "POST",
      headers: createHeaders(apiKey),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Failed to stream team: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        onDone();
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process SSE events
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6).trim();

          if (data === "[DONE]") {
            onDone();
            return;
          }

          try {
            const event = JSON.parse(data);
            onChunk(event);
          } catch (e) {
            if (data) {
              onChunk({ type: "content", content: data });
            }
          }
        }
      }
    }
  } catch (error) {
    onError(error);
  }
};

// ============================================================================
// Thread API
// ============================================================================

/**
 * Get list of threads for a resource
 */
export const getThreads = async (
  serverUrl,
  apiKey,
  resourceType,
  resourceId,
) => {
  const params = new URLSearchParams();
  if (resourceType) params.append("resource_type", resourceType);
  if (resourceId) params.append("resource_id", resourceId);

  const response = await fetch(`${serverUrl}/threads?${params}`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch threads: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Create a new thread
 */
export const createThread = async (serverUrl, apiKey, data) => {
  const response = await fetch(`${serverUrl}/threads`, {
    method: "POST",
    headers: createHeaders(apiKey),
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to create thread: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Get a thread by ID
 */
export const getThread = async (serverUrl, apiKey, threadId) => {
  const response = await fetch(`${serverUrl}/threads/${threadId}`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch thread: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Get messages for a thread
 */
export const getThreadMessages = async (serverUrl, apiKey, threadId) => {
  const response = await fetch(`${serverUrl}/threads/${threadId}/messages`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch messages: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Delete a thread
 */
export const deleteThread = async (serverUrl, apiKey, threadId) => {
  const response = await fetch(`${serverUrl}/threads/${threadId}`, {
    method: "DELETE",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to delete thread: ${response.statusText}`);
  }

  return response.json();
};
