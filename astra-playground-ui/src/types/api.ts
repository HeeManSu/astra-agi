/**
 * API response/request types mirroring the Astra runtime Pydantic models at
 * astra/runtime/src/runtime/routes/. Edit only when the runtime contracts change.
 */

// -- Auth ---------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
}

// -- Agents / Teams -----------------------------------------------------

export interface Agent {
  id: string;
  name: string;
  description: string | null;
}

export interface Team {
  id: string;
  name: string;
  description: string | null;
}

export interface AgentRunRequest {
  message: string;
  thread_id?: string | null;
  context?: Record<string, unknown> | null;
}

export type TeamRunRequest = AgentRunRequest;

export interface InvokeResponse {
  response: string;
  timing_ms: number;
}

// -- Threads ------------------------------------------------------------

export type ResourceType = "agent" | "team" | "stepper" | "workflow";

export interface ThreadCreate {
  resource_type: ResourceType;
  resource_id: string;
  resource_name: string;
  title?: string;
  metadata?: Record<string, unknown> | null;
}

export interface Thread {
  id: string;
  resource_type: ResourceType;
  resource_id: string;
  resource_name: string;
  title: string;
  created_at: string; // ISO datetime
  updated_at: string | null;
  metadata: Record<string, unknown> | null;
}

export interface ThreadMessage {
  id: string;
  thread_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  sequence: number;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

export interface DeleteThreadResponse {
  success: boolean;
  message: string;
}

// -- Tools --------------------------------------------------------------

export interface Tool {
  id: string;
  slug: string;
  name: string;
  source: string;
  description: string | null;
  input_schema: Record<string, unknown> | null;
  output_schema: Record<string, unknown> | null;
  required_fields: string[] | null;
  version: string | null;
  is_active: boolean;
  hash: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ToolListResponse {
  tools: Tool[];
  total: number;
  page: number;
  page_size: number;
}

export interface ToolUpdateRequest {
  name?: string;
  description?: string;
  input_schema?: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  is_active?: boolean;
}

export interface ToolSyncResponse {
  message: string;
  report: Record<string, unknown>;
}

// -- Observability ------------------------------------------------------

export type TraceStatus = "RUNNING" | "SUCCESS" | "ERROR";
export type SpanStatus = "RUNNING" | "SUCCESS" | "ERROR";
export type SpanKind = "WORKFLOW" | "STEP" | "GENERATION" | "TOOL";
export type LogLevel = "DEBUG" | "INFO" | "WARN" | "WARNING" | "ERROR";

export interface Trace {
  trace_id: string;
  name: string;
  status: TraceStatus;
  start_time: string;
  end_time: string | null;
  attributes: Record<string, unknown>;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  thoughts_tokens: number;
  model: string | null;
  duration_ms: number | null;
}

export interface Span {
  span_id: string;
  trace_id: string;
  parent_span_id: string | null;
  name: string;
  kind: SpanKind;
  status: SpanStatus;
  start_time: string;
  end_time: string | null;
  duration_ms: number | null;
  attributes: Record<string, unknown>;
  error: string | null;
}

export interface Log {
  id: string;
  trace_id: string;
  span_id: string | null;
  level: LogLevel;
  message: string;
  attributes: Record<string, unknown>;
  timestamp: string;
}

export interface TraceListResponse {
  traces: Trace[];
  count: number;
}

export interface TraceDetailResponse {
  trace: Trace;
  spans: Span[];
}

export interface LogListResponse {
  logs: Log[];
  count: number;
}

// -- Health -------------------------------------------------------------

export interface HealthResponse {
  status: "healthy" | "degraded" | "starting" | "unhealthy";
  liveness: Record<string, unknown>;
  readiness: Record<string, unknown>;
  startup: Record<string, unknown>;
}
