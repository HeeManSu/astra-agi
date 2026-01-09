/**
 * ToolCallDisplay - Collapsible tool call component (Mastra-style)
 * Shows tool name, arguments, and results in an expandable dropdown
 */
import { useState } from "react";
import { ChevronDown, ChevronRight, Sparkles, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  status: "pending" | "running" | "completed" | "error";
}

interface ToolCallDisplayProps {
  toolCall: ToolCall;
}

export function ToolCallDisplay({ toolCall }: ToolCallDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copiedArgs, setCopiedArgs] = useState(false);
  const [copiedResult, setCopiedResult] = useState(false);

  const handleCopy = async (text: string, type: "args" | "result") => {
    await navigator.clipboard.writeText(text);
    if (type === "args") {
      setCopiedArgs(true);
      setTimeout(() => setCopiedArgs(false), 2000);
    } else {
      setCopiedResult(true);
      setTimeout(() => setCopiedResult(false), 2000);
    }
  };

  const argsJson = JSON.stringify(toolCall.arguments, null, 2);
  const resultJson = toolCall.result
    ? JSON.stringify(toolCall.result, null, 2)
    : null;

  return (
    <div className="my-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors",
          "bg-[#1a1a1a] hover:bg-[#252525] border border-[#333]",
          toolCall.status === "running" && "animate-pulse"
        )}
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        )}
        <Sparkles className="h-3 w-3 text-amber-500" />
        <span className="font-mono text-xs text-foreground">
          {toolCall.name}
        </span>
        {toolCall.status === "running" && (
          <span className="text-xs text-muted-foreground ml-2">running...</span>
        )}
      </button>

      {isExpanded && (
        <div className="mt-2 ml-4 space-y-3 border-l-2 border-[#333] pl-4">
          {/* Tool Arguments */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">
                Tool arguments
              </span>
              <button
                onClick={() => handleCopy(argsJson, "args")}
                className="p-1 hover:bg-[#252525] rounded transition-colors"
              >
                {copiedArgs ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3 text-muted-foreground" />
                )}
              </button>
            </div>
            <pre className="bg-[#0a0a0a] rounded-md p-3 text-xs font-mono overflow-x-auto border border-[#222]">
              <code className="text-[#e6db74]">{argsJson}</code>
            </pre>
          </div>

          {/* Tool Result */}
          {resultJson && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Tool result
                </span>
                <button
                  onClick={() => handleCopy(resultJson, "result")}
                  className="p-1 hover:bg-[#252525] rounded transition-colors"
                >
                  {copiedResult ? (
                    <Check className="h-3 w-3 text-green-500" />
                  ) : (
                    <Copy className="h-3 w-3 text-muted-foreground" />
                  )}
                </button>
              </div>
              <pre className="bg-[#0a0a0a] rounded-md p-3 text-xs font-mono overflow-x-auto max-h-64 border border-[#222]">
                <code className="text-[#e6db74]">{resultJson}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Parse thinking content and tool mentions from text
 */
export function parseMessageContent(content: string): {
  thinking: string | null;
  toolMentions: string[];
  mainContent: string;
} {
  // Extract thinking block
  const thinkingMatch = content.match(/<thinking>([\s\S]*?)<\/thinking>/);
  const thinking = thinkingMatch ? thinkingMatch[1].trim() : null;

  // Remove thinking block from content
  let mainContent = content
    .replace(/<thinking>[\s\S]*?<\/thinking>/g, "")
    .trim();

  // Extract tool mentions (text like `toolName` in backticks)
  const toolMentions: string[] = [];
  const toolMentionRegex = /`([a-zA-Z_][a-zA-Z0-9_]*Tool)`/g;
  let match;
  while ((match = toolMentionRegex.exec(content)) !== null) {
    if (!toolMentions.includes(match[1])) {
      toolMentions.push(match[1]);
    }
  }

  return { thinking, toolMentions, mainContent };
}

/**
 * ThinkingBlock - Displays the thinking/reasoning section
 */
export function ThinkingBlock({ content }: { content: string }) {
  // Highlight tool names in the thinking text
  const highlightTools = (text: string) => {
    return text.replace(
      /`([a-zA-Z_][a-zA-Z0-9_]*Tool)`/g,
      '<span class="inline-block px-1.5 py-0.5 rounded bg-[#252525] font-mono text-xs border border-[#444]">$1</span>'
    );
  };

  return (
    <div className="text-foreground/80 mb-4">
      <span className="text-muted-foreground">&lt;thinking&gt;</span>
      <span
        dangerouslySetInnerHTML={{ __html: highlightTools(content) }}
        className="mx-1"
      />
      <span className="text-muted-foreground">&lt;/thinking&gt;</span>
    </div>
  );
}
