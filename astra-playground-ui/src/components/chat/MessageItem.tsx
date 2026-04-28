import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Message } from "@/types/domain";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { ToolCallCard } from "./ToolCallCard";

interface MessageItemProps {
  message: Message;
  isStreaming: boolean;
  isLast: boolean;
}

export function MessageItem({ message, isStreaming, isLast }: MessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3 message-fade-in",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser && (
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
          <Bot className="h-4 w-4 text-primary" />
        </div>
      )}

      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted",
        )}
      >
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mb-3 space-y-2">
            {message.tool_calls.map((tool, idx) => (
              <ToolCallCard key={idx} tool={tool} />
            ))}
          </div>
        )}

        {message.content ? (
          <MarkdownRenderer content={message.content} />
        ) : (
          <span className="text-muted-foreground">Thinking...</span>
        )}
        {isStreaming && isLast && message.role === "assistant" && (
          <span className="streaming-cursor" />
        )}
      </div>

      {isUser && (
        <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
