import { Bot, Wrench, GitBranch, Copy, MemoryStick, X } from "lucide-react";
import type { Agent } from "@/lib/types";

interface AgentInformationProps {
  agent: Agent;
  agentId: string;
  isCollapsed?: boolean;
  onToggle?: () => void;
}

export function AgentInformation({
  agent,
  agentId,
  isCollapsed = false,
  onToggle,
}: AgentInformationProps) {
  if (isCollapsed) {
    return (
      <aside className="hidden lg:block w-0 overflow-hidden transition-all duration-300 border-l border-border">
        <div className="w-[300px]" />
      </aside>
    );
  }

  return (
    <aside className="hidden lg:flex w-[300px] border-l border-border overflow-auto transition-all duration-300">
      <div className="p-4 space-y-6">
        {/* Agent Info */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Bot className="h-5 w-5 text-primary" />
            <h2 className="font-semibold flex-1">{agent.name}</h2>
            {onToggle && (
              <button
                onClick={onToggle}
                className="p-1 text-muted-foreground hover:text-foreground transition-colors"
                title="Close sidebar"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <p className="text-xs text-muted-foreground font-mono">{agentId}</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 border-b border-border pb-2">
          <button className="text-sm text-foreground">Overview</button>
          <button className="text-sm text-muted-foreground hover:text-foreground">
            Model Settings
          </button>
          <button className="text-sm text-muted-foreground hover:text-foreground">
            Memory
          </button>
        </div>

        {/* Model */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium flex items-center gap-2">Model</h3>
          <div className="flex items-center gap-2 rounded-md bg-secondary px-3 py-2">
            <div className="h-6 w-6 rounded bg-amber-500/20 flex items-center justify-center">
              <span className="text-xs">🤖</span>
            </div>
            <span className="text-xs font-mono truncate">
              {agent.model || "unknown"}
            </span>
          </div>
        </div>

        {/* Memory */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <MemoryStick className="h-4 w-4" />
            Memory
          </h3>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-primary" />
            <span className="text-sm">On</span>
          </div>
        </div>

        {/* Tools */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            Tools
          </h3>
          {agent.tools > 0 ? (
            <div className="text-sm text-muted-foreground">
              {agent.tools} {agent.tools === 1 ? "tool" : "tools"} configured
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No tools</p>
          )}
        </div>

        {/* Workflows */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            Workflows
          </h3>
          <p className="text-sm text-muted-foreground">No workflows</p>
        </div>

        {/* System Prompt */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">System Prompt</h3>
            <button className="p-1 text-muted-foreground hover:text-foreground">
              <Copy className="h-4 w-4" />
            </button>
          </div>
          <div className="rounded-md bg-secondary p-3 text-xs text-muted-foreground max-h-[200px] overflow-auto font-mono">
            {agent.instructions || "No system prompt defined"}
          </div>
        </div>
      </div>
    </aside>
  );
}
