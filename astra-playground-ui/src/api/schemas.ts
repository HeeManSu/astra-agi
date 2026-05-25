/**
 * Zod schemas for runtime API responses + SSE events. Each network call uses
 * `Schema.parse(json)` to fail loud on shape drift.
 *
 * The SSE union is intentionally permissive: it accepts the canonical
 * `{ event_type, data }` form AND the legacy fallbacks the original ChatArea
 * tolerated (`{ type, content }`, `{ delta: { content } }`, `{ timing_ms }`).
 * Unknown shapes are silently ignored rather than throwing — see
 * `safeParseSseEvent`.
 */

import { z } from "zod";
import type { StreamEvent } from "@/types/sse";

// ---------- Auth ------------------------------------------------------

export const TokenResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.literal("Bearer").default("Bearer"),
  expires_in: z.number(),
});

// ---------- Agents / Teams -------------------------------------------

export const AgentSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
});

export const TeamSchema = AgentSchema;

export const InvokeResponseSchema = z.object({
  response: z.string(),
  timing_ms: z.number(),
});

// ---------- Threads --------------------------------------------------

const ResourceTypeSchema = z.enum([
  "agent",
  "team",
  "stepper",
  "workflow",
]);

export const ThreadSchema = z.object({
  id: z.string(),
  resource_type: ResourceTypeSchema,
  resource_id: z.string(),
  resource_name: z.string(),
  title: z.string(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
  metadata: z.record(z.string(), z.unknown()).nullable(),
});

export const ThreadMessageSchema = z.object({
  id: z.string(),
  thread_id: z.string(),
  role: z.enum(["user", "assistant", "system", "tool"]),
  content: z.string(),
  sequence: z.number(),
  created_at: z.string(),
  metadata: z.record(z.string(), z.unknown()).nullable(),
});

export const DeleteThreadResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

// ---------- Tools ----------------------------------------------------

export const ToolSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  source: z.string(),
  description: z.string().nullable(),
  input_schema: z.record(z.string(), z.unknown()).nullable(),
  output_schema: z.record(z.string(), z.unknown()).nullable(),
  required_fields: z.array(z.string()).nullable(),
  version: z.string().nullable(),
  is_active: z.boolean(),
  hash: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
});

export const ToolListResponseSchema = z.object({
  tools: z.array(ToolSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
});

export const ToolSyncResponseSchema = z.object({
  message: z.string(),
  report: z.record(z.string(), z.unknown()),
});

// ---------- Observability --------------------------------------------

const TraceStatusSchema = z.enum(["RUNNING", "SUCCESS", "ERROR"]);
const SpanStatusSchema = z.enum(["RUNNING", "SUCCESS", "ERROR"]);
const SpanKindSchema = z.enum(["WORKFLOW", "STEP", "GENERATION", "TOOL"]);
const LogLevelSchema = z.enum(["DEBUG", "INFO", "WARN", "WARNING", "ERROR"]);

const TraceSchema = z.object({
  trace_id: z.string(),
  name: z.string(),
  status: TraceStatusSchema,
  start_time: z.string(),
  end_time: z.string().nullable(),
  attributes: z.record(z.string(), z.unknown()),
  total_tokens: z.number(),
  input_tokens: z.number(),
  output_tokens: z.number(),
  thoughts_tokens: z.number(),
  model: z.string().nullable(),
  duration_ms: z.number().nullable(),
});

const SpanSchema = z.object({
  span_id: z.string(),
  trace_id: z.string(),
  parent_span_id: z.string().nullable(),
  name: z.string(),
  kind: SpanKindSchema,
  status: SpanStatusSchema,
  start_time: z.string(),
  end_time: z.string().nullable(),
  duration_ms: z.number().nullable(),
  attributes: z.record(z.string(), z.unknown()),
  error: z.string().nullable(),
});

const LogSchema = z.object({
  id: z.string(),
  trace_id: z.string(),
  span_id: z.string().nullable(),
  level: LogLevelSchema,
  message: z.string(),
  attributes: z.record(z.string(), z.unknown()),
  timestamp: z.string(),
});

export const TraceListResponseSchema = z.object({
  traces: z.array(TraceSchema),
  count: z.number(),
});

export const TraceDetailResponseSchema = z.object({
  trace: TraceSchema,
  spans: z.array(SpanSchema),
});

export const LogListResponseSchema = z.object({
  logs: z.array(LogSchema),
  count: z.number(),
});

export const TopItemSchema = z.object({
  name: z.string(),
  count: z.number(),
  extra: z.record(z.string(), z.unknown()).default({}),
});

export const MetricsResponseSchema = z.object({
  window_start: z.string(),
  window_end: z.string(),
  trace_sample_size: z.number(),
  truncated: z.boolean(),
  request_count: z.number(),
  success_count: z.number(),
  error_count: z.number(),
  running_count: z.number(),
  success_rate: z.number(),
  error_rate: z.number(),
  latency_p50_ms: z.number().nullable(),
  latency_p95_ms: z.number().nullable(),
  latency_p99_ms: z.number().nullable(),
  latency_avg_ms: z.number().nullable(),
  total_tokens: z.number(),
  input_tokens: z.number(),
  output_tokens: z.number(),
  thoughts_tokens: z.number(),
  avg_tokens_per_request: z.number(),
  avg_ttft_ms: z.number().nullable(),
  generation_p50_ms: z.number().nullable(),
  generation_p95_ms: z.number().nullable(),
  top_models: z.array(TopItemSchema),
  top_tools: z.array(TopItemSchema),
  top_agents: z.array(TopItemSchema),
  top_teams: z.array(TopItemSchema),
  tool_call_count: z.number(),
  tool_error_count: z.number(),
  tool_error_rate: z.number(),
});

// ---------- SSE events ----------------------------------------------

const StatusEventSchema = z.object({
  event_type: z.literal("status"),
  data: z.object({ message: z.string() }).passthrough(),
});

const ContentEventSchema = z.object({
  event_type: z.literal("content"),
  data: z.object({ text: z.string() }).passthrough(),
});

const ToolCallEventSchema = z.object({
  event_type: z.literal("tool_call"),
  data: z
    .object({
      index: z.number(),
      tool_name: z.string(),
      arguments: z.record(z.string(), z.unknown()).optional(),
    })
    .passthrough(),
});

const ToolResultEventSchema = z.object({
  event_type: z.literal("tool_result"),
  data: z
    .object({
      index: z.number(),
      tool_name: z.string().optional(),
      result: z.unknown(),
    })
    .passthrough(),
});

const ErrorEventSchema = z.object({
  event_type: z.literal("error"),
  data: z.object({ message: z.string() }).passthrough(),
});

const DoneEventSchema = z.object({
  event_type: z.literal("done"),
  data: z.object({ status: z.string().optional() }).passthrough(),
});

const SynthesizeEventSchema = z.object({
  event_type: z.literal("synthesize"),
  data: z.object({ message: z.string() }).passthrough(),
});

// Legacy fallbacks observed in older runtime versions
const LegacyContentEventSchema = z.object({
  type: z.literal("content"),
  content: z.string(),
});

const LegacyDeltaEventSchema = z.object({
  delta: z.object({ content: z.string() }),
});

const TimingEventSchema = z.object({
  timing_ms: z.number(),
});

const StreamEventSchema = z.union([
  StatusEventSchema,
  ContentEventSchema,
  ToolCallEventSchema,
  ToolResultEventSchema,
  ErrorEventSchema,
  DoneEventSchema,
  SynthesizeEventSchema,
  LegacyContentEventSchema,
  LegacyDeltaEventSchema,
  TimingEventSchema,
]);

/**
 * Permissive parser: returns the parsed event if it matches any known shape,
 * otherwise null (caller decides whether to warn). Falls back to wrapping
 * non-JSON strings as `{ type: "content", content: data }` to mirror
 * historical behavior from the original ChatArea.
 */
export function safeParseSseEvent(raw: string): StreamEvent | null {
  try {
    const parsed: unknown = JSON.parse(raw);
    const result = StreamEventSchema.safeParse(parsed);
    if (result.success) {
      return result.data as StreamEvent;
    }
    return null;
  } catch {
    if (raw) {
      return { type: "content", content: raw };
    }
    return null;
  }
}
