/**
 * Server-Sent Event types emitted by /agents/{id}/stream and /teams/{id}/stream.
 *
 * Canonical form: `{ event_type, data }` with discriminated `event_type`.
 * Legacy fallbacks accepted (and seen historically in ChatArea):
 *   - `{ type: "content", content: string }`
 *   - `{ delta: { content: string } }`
 *   - bare string
 *
 * Phase 4 lands a Zod schema that parses each line into one of these variants.
 */

export type StreamEventType =
  | "status"
  | "content"
  | "tool_call"
  | "tool_result"
  | "error"
  | "done"
  | "synthesize";

interface BaseEvent<T extends StreamEventType, D> {
  event_type: T;
  data: D;
}

export type StatusEvent = BaseEvent<"status", { message: string }>;

export type ContentEvent = BaseEvent<"content", { text: string }>;

export interface ToolCallPayload {
  index: number;
  tool_name: string;
  arguments?: Record<string, unknown>;
}

export type ToolCallEvent = BaseEvent<"tool_call", ToolCallPayload>;

export interface ToolResultPayload {
  index: number;
  tool_name?: string;
  result: unknown;
}

export type ToolResultEvent = BaseEvent<"tool_result", ToolResultPayload>;

export type ErrorEvent = BaseEvent<"error", { message: string }>;

export type DoneEvent = BaseEvent<"done", { status?: string }>;

export type SynthesizeEvent = BaseEvent<"synthesize", { message: string }>;

export type CanonicalStreamEvent =
  | StatusEvent
  | ContentEvent
  | ToolCallEvent
  | ToolResultEvent
  | ErrorEvent
  | DoneEvent
  | SynthesizeEvent;

// Legacy / fallback shapes preserved so the new parser doesn't regress
// behavior already handled in the JSX ChatArea.
export interface LegacyContentEvent {
  type: "content";
  content: string;
}

export interface LegacyDeltaEvent {
  delta: { content: string };
}

export interface TimingEvent {
  timing_ms: number;
}

export type StreamEvent =
  | CanonicalStreamEvent
  | LegacyContentEvent
  | LegacyDeltaEvent
  | TimingEvent;

export type StreamCallbacks = {
  onChunk: (event: StreamEvent) => void;
  onDone: () => void;
  onError: (error: Error) => void;
};
