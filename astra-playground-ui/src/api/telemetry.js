const API_BASE = "/api"; // In development, this is proxied or absolute URL

export async function getTraces(serverUrl, apiKey, limit = 50, offset = 0) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  // Handle trailing slash in serverUrl
  const baseUrl = serverUrl.replace(/\/$/, "");

  const response = await fetch(
    `${baseUrl}/observability/traces?limit=${limit}&offset=${offset}`,
    {
      method: "GET",
      headers,
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch traces: ${response.statusText}`);
  }

  return response.json();
}

export async function getTraceDetail(serverUrl, apiKey, traceId) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  const baseUrl = serverUrl.replace(/\/$/, "");

  const response = await fetch(`${baseUrl}/observability/traces/${traceId}`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch trace detail: ${response.statusText}`);
  }

  return response.json();
}

export async function getLogsForTrace(serverUrl, apiKey, traceId, limit = 500) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  const baseUrl = serverUrl.replace(/\/$/, "");

  const response = await fetch(
    `${baseUrl}/observability/traces/${traceId}/logs?limit=${limit}`,
    {
      method: "GET",
      headers,
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch logs: ${response.statusText}`);
  }

  return response.json();
}
