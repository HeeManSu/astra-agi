import { Loader2 } from "lucide-react";
import type { ToolCall } from "@/types/domain";

interface ToolCallCardProps {
  tool: ToolCall;
}

export function ToolCallCard({ tool }: ToolCallCardProps) {
  const hasResult = tool.result !== undefined && tool.result !== null;
  const renderedResult =
    typeof tool.result === "string" ? tool.result : JSON.stringify(tool.result);

  return (
    <div className="bg-background/50 rounded p-2 text-xs border border-border">
      <div className="flex items-center justify-between gap-2 font-mono text-muted-foreground mb-1">
        <span className="flex items-center gap-1">
          {tool.status === "complete" ? (
            <span className="text-green-500">✓</span>
          ) : (
            <Loader2 className="h-3 w-3 animate-spin" />
          )}
          {tool.tool_name || "Unknown Tool"}
        </span>
      </div>
      {hasResult && (
        <div className="pl-4 border-l-2 border-border/50 mt-1 max-h-20 overflow-y-auto text-muted-foreground/80">
          {renderedResult}
        </div>
      )}
    </div>
  );
}
