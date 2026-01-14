import { useParams } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import { ArrowLeft, Send, Users, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useTeam } from "@/hooks/use-teams";
import { streamTeamResponse } from "@/lib/api";
import ReactMarkdown from "react-markdown";

interface Message {
  id: string;
  role: "user" | "assistant" | "status";
  content: string;
  timestamp: Date;
}

export function TeamChatPage() {
  const { teamId } = useParams<{ teamId: string }>();
  const { data: team, isLoading: teamLoading } = useTeam(teamId);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !teamId || isStreaming) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);

    // Create assistant message placeholder
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      },
    ]);

    try {
      const stream = streamTeamResponse(teamId, {
        message: userMessage.content,
      });
      let fullContent = "";

      for await (const event of stream) {
        switch (event.type) {
          case "status":
          case "code_generated": {
            const data = event.data as { message?: string };
            // Update with status message
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: data.message || fullContent }
                  : m
              )
            );
            break;
          }
          case "token":
          case "content": {
            const data = event.data as { content?: string; text?: string };
            fullContent += data.content || data.text || "";
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: fullContent } : m
              )
            );
            break;
          }
          case "tool_call": {
            const data = event.data as { tool_name?: string };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: `Calling tool: ${data.tool_name}...` }
                  : m
              )
            );
            break;
          }
          case "done":
            break;
          case "error": {
            const data = event.data as { message?: string; error?: string };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content: `Error: ${
                        data.message || data.error || "Unknown error"
                      }`,
                    }
                  : m
              )
            );
            break;
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: `Error: ${(err as Error).message}` }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  if (teamLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center gap-4 border-b border-border px-6 py-4">
        <Link
          to="/teams"
          className="p-1 hover:bg-secondary rounded-md transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <div>
            <h1 className="font-semibold">{team?.name || teamId}</h1>
            <p className="text-xs text-muted-foreground">
              {team?.member_count || 0} members • {team?.model || "unknown"}
            </p>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <Users className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-sm">Start a conversation with the team</p>
            <p className="text-xs mt-1">{team?.description}</p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-foreground"
              }`}
            >
              {message.role === "assistant" ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>{message.content || "..."}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-border px-6 py-4"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Send a message to the team..."
            className="flex-1 rounded-md border border-border bg-input px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            disabled={isStreaming}
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
