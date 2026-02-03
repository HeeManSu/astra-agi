/**
 * Tools API Client
 *
 * Handles all API calls for tool definitions.
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
 * Get list of tool definitions
 */
export const getTools = async (
  serverUrl,
  apiKey,
  { search = "", source = "", page = 1, pageSize = 50 } = {},
) => {
  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (source) params.append("source", source);
  params.append("page", page.toString());
  params.append("page_size", pageSize.toString());

  const response = await fetch(`${serverUrl}/tools?${params}`, {
    method: "GET",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch tools: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Get a single tool by slug
 */
export const getTool = async (serverUrl, apiKey, slug) => {
  const response = await fetch(
    `${serverUrl}/tools/${encodeURIComponent(slug)}`,
    {
      method: "GET",
      headers: createHeaders(apiKey),
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch tool: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Update a tool definition
 */
export const updateTool = async (serverUrl, apiKey, slug, data) => {
  const response = await fetch(
    `${serverUrl}/tools/${encodeURIComponent(slug)}`,
    {
      method: "PUT",
      headers: createHeaders(apiKey),
      body: JSON.stringify(data),
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to update tool: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Delete a tool definition
 */
export const deleteTool = async (serverUrl, apiKey, slug) => {
  const response = await fetch(
    `${serverUrl}/tools/${encodeURIComponent(slug)}`,
    {
      method: "DELETE",
      headers: createHeaders(apiKey),
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to delete tool: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Trigger tool sync
 */
export const syncTools = async (serverUrl, apiKey) => {
  const response = await fetch(`${serverUrl}/tools/sync`, {
    method: "POST",
    headers: createHeaders(apiKey),
  });

  if (!response.ok) {
    throw new Error(`Failed to sync tools: ${response.statusText}`);
  }

  return response.json();
};
