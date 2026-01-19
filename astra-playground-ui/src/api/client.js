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
export const runAgent = async (serverUrl, apiKey, agentId, message) => {
  const response = await fetch(`${serverUrl}/agents/${agentId}/invoke`, {
    method: "POST",
    headers: createHeaders(apiKey),
    body: JSON.stringify({ message }),
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
  onError
) => {
  try {
    const response = await fetch(`${serverUrl}/agents/${agentId}/stream`, {
      method: "POST",
      headers: createHeaders(apiKey),
      body: JSON.stringify({ message }),
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
export const runTeam = async (serverUrl, apiKey, teamId, message) => {
  const response = await fetch(`${serverUrl}/teams/${teamId}/invoke`, {
    method: "POST",
    headers: createHeaders(apiKey),
    body: JSON.stringify({ message }),
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
  onError
) => {
  try {
    const response = await fetch(`${serverUrl}/teams/${teamId}/stream`, {
      method: "POST",
      headers: createHeaders(apiKey),
      body: JSON.stringify({ message }),
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
