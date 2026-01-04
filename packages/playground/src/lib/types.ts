// Types for Astra API responses

export interface Agent {
  id: string;
  name: string;
  description?: string;
  model?: {
    provider: string;
    model_id: string;
  };
  tools: string[];
  instructions?: string;
}

export interface Tool {
  name: string;
  description?: string;
  agents: string[];
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
  agent_id: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
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
  type: "content" | "tool_call" | "tool_result" | "done" | "error";
  data: unknown;
}

export interface ServerInfo {
  name: string;
  version: string;
  agents: string[];
  uptime: number;
}
