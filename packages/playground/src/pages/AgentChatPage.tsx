import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import {
  getAgent,
  getThreads,
  createThread,
  getMessages,
  streamGenerate,
} from "@/lib/api";
import type { Message } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Bot,
  Plus,
  Send,
  Mic,
  Paperclip,
  ChevronRight,
  Wrench,
  GitBranch,
  Copy,
  MemoryStick,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

export function AgentChatPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const queryClient = useQueryClient();
  const [selectedThread, setSelectedThread] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "traces" | "evals">(
    "chat"
  );

  // Fetch agent details
  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ["agent", agentId],
    queryFn: () => getAgent(agentId!),
    enabled: !!agentId,
  });

  // Fetch threads
  const { data: threads } = useQuery({
    queryKey: ["threads", agentId],
    queryFn: () => getThreads(agentId!),
    enabled: !!agentId,
  });

  // Fetch messages for selected thread
  const { data: messages } = useQuery({
    queryKey: ["messages", selectedThread],
    queryFn: () => getMessages(selectedThread!),
    enabled: !!selectedThread,
  });

  // Create new thread
  const createThreadMutation = useMutation({
    mutationFn: () => createThread(agentId!),
    onSuccess: (thread) => {
      queryClient.invalidateQueries({ queryKey: ["threads", agentId] });
      setSelectedThread(thread.id);
    },
  });

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Handle send message with streaming
  const handleSend = async () => {
    if (!input.trim() || !agentId || isStreaming) return;

    let threadId = selectedThread;
    if (!threadId) {
      const thread = await createThreadMutation.mutateAsync();
      threadId = thread.id;
    }

    const userMessage = input;
    setInput("");
    setIsStreaming(true);
    setStreamingContent("");

    try {
      // Use the new generate endpoint that handles message saving
      for await (const chunk of streamGenerate(threadId, userMessage)) {
        setStreamingContent((prev) => prev + chunk);
      }
      // Refresh messages after streaming completes
      await queryClient.invalidateQueries({ queryKey: ["messages", threadId] });
    } catch (error) {
      console.error("Streaming error:", error);
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
    }
  };

  if (agentLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
        <Bot className="h-12 w-12 mb-4 opacity-50" />
        <p>Agent not found</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Sessions Sidebar */}
      <aside className="w-[220px] flex flex-col border-r border-border">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1 border-b border-border px-4 py-3 text-sm">
          <Link
            to="/agents"
            className="text-muted-foreground hover:text-foreground"
          >
            <Bot className="h-4 w-4" />
          </Link>
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
          <span className="text-foreground truncate">{agent.name}</span>
        </div>

        {/* New Chat Button */}
        <div className="border-b border-border p-2">
          <button
            onClick={() => createThreadMutation.mutate()}
            className="flex w-full items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            New Chat
          </button>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {threads?.map((thread) => (
            <button
              key={thread.id}
              onClick={() => setSelectedThread(thread.id)}
              className={cn(
                "w-full rounded-md px-3 py-2 text-left text-sm transition-colors",
                selectedThread === thread.id
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <p className="truncate font-medium">Chat Session</p>
              <p className="text-xs text-muted-foreground">
                {new Date(thread.created_at).toLocaleDateString()}
              </p>
            </button>
          ))}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header with Tabs */}
        <header className="flex items-center justify-between border-b border-border px-4 py-2">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4" />
              <span className="font-medium">{agent.name}</span>
            </div>
            <nav className="flex gap-4">
              {(["chat", "traces", "evals"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "text-sm capitalize transition-colors",
                    activeTab === tab
                      ? "text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {tab}
                </button>
              ))}
            </nav>
          </div>
        </header>

        {/* Chat Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Messages */}
          <div className="flex-1 flex flex-col">
            <div className="flex-1 overflow-auto p-4 space-y-4">
              {messages?.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {streamingContent && (
                <MessageBubble
                  message={{
                    id: "streaming",
                    thread_id: "",
                    role: "assistant",
                    content: streamingContent,
                    created_at: new Date().toISOString(),
                  }}
                />
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-border p-4">
              <div className="flex items-center gap-2 rounded-lg border border-border bg-input p-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) =>
                    e.key === "Enter" && !e.shiftKey && handleSend()
                  }
                  placeholder="Enter your message..."
                  disabled={isStreaming}
                  className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
                />
                <button className="p-1.5 text-muted-foreground hover:text-foreground">
                  <Mic className="h-4 w-4" />
                </button>
                <button className="p-1.5 text-muted-foreground hover:text-foreground">
                  <Paperclip className="h-4 w-4" />
                </button>
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
                  className="rounded-md bg-secondary p-1.5 text-foreground transition-colors hover:bg-secondary/80 disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Agent Details Sidebar */}
          <aside className="w-[300px] border-l border-border overflow-auto">
            <div className="p-4 space-y-6">
              {/* Agent Info */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Bot className="h-5 w-5 text-primary" />
                  <h2 className="font-semibold">{agent.name}</h2>
                </div>
                <p className="text-xs text-muted-foreground font-mono">
                  {agentId}
                </p>
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
                <h3 className="text-sm font-medium flex items-center gap-2">
                  Model
                </h3>
                <div className="flex items-center gap-2 rounded-md bg-secondary px-3 py-2">
                  <div className="h-6 w-6 rounded bg-amber-500/20 flex items-center justify-center">
                    <span className="text-xs">🤖</span>
                  </div>
                  <span className="text-sm">
                    {agent.model?.provider || "unknown"}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground truncate max-w-[120px]">
                    {agent.model?.model_id}
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
                {agent.tools.length > 0 ? (
                  <div className="space-y-1">
                    {agent.tools.map((tool) => (
                      <div key={tool} className="text-sm text-muted-foreground">
                        {tool}
                      </div>
                    ))}
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
        </div>
      </div>
    </div>
  );
}

// Message bubble component
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "justify-end")}>
      {!isUser && (
        <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[70%] rounded-lg px-4 py-2",
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary"
        )}
      >
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
      {isUser && (
        <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
          <span className="text-xs">You</span>
        </div>
      )}
    </div>
  );
}
