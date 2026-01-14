// Types for Astra API responses

export interface Agent {
  id: string;
  name: string;
  description?: string;
  model: string; // Model ID (e.g., "gemini-2.0-flash-exp", "apac.amazon.nova-pro-v1:0")
  tools: number; // Number of tools (count)
  instructions?: string;
}

export interface TeamMember {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  execution_mode: string;
  member_count: number;
  model: string;
  members?: TeamMember[];
  configuration?: {
    max_delegations: number;
    timeout: number;
    member_timeout: number;
    allow_parallel: boolean;
    max_parallel: number;
    max_recursion_depth: number;
  };
}

export interface ToolParameter {
  name: string;
  type: string;
  description?: string;
  required: boolean;
  default?: unknown;
}

export interface Tool {
  name: string;
  description?: string;
  parameters: ToolParameter[];
  agent_names: string[];
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  steps: WorkflowStep[];
}

export interface WorkflowStep {
  id: string;
  type: "agent" | "tool" | "condition";
  config: Record<string, unknown>;
}

export interface Thread {
  id: string;
  agent_name: string;
  title?: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  thread_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  created_at: string;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: string;
  result?: string;
}

export interface StreamEvent {
  type:
    | "thinking"
    | "token"
    | "content"
    | "status"
    | "code_generated"
    | "tool_start"
    | "tool_call"
    | "tool_result"
    | "done"
    | "error";
  data: unknown;
}

export interface ServerInfo {
  name: string;
  version: string;
  agents: string[];
  uptime: number;
}
