/**
 * UI-only types — distinct from API types so we can shape Redux state and
 * component props independently of how the runtime serializes things.
 */

export type ActiveTab =
  | "agents"
  | "teams"
  | "settings"
  | "telemetry"
  | "tools";

export type SelectedItemType = "agent" | "team";

export interface SelectedItem {
  type: SelectedItemType;
  id: string;
  data?: Record<string, unknown>;
}

/**
 * Session keys shape: `agent:<id>` for ephemeral agent chats,
 * `team:<id>` for ephemeral team chats, `thread:<uuid>` once a
 * thread is opened or created. Stored as a string for Redux serializability.
 */
export type SessionKey = `agent:${string}` | `team:${string}` | `thread:${string}`;

export interface ToolCall {
  index: number;
  tool_name: string;
  arguments?: Record<string, unknown>;
  result?: unknown;
  status: "running" | "complete";
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: string; // ISO datetime
  tool_calls?: ToolCall[];
  metadata?: Record<string, unknown>;
}

export type ChatMode = "stream" | "invoke";
