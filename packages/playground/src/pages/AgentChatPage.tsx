import { useParams, useSearchParams } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import {
  generateAgentResponse,
  streamAgentResponse,
  type GenerateRequest,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Bot,
  Send,
  Zap,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Menu,
  Check,
  Copy,
  AlertCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

// Import custom hooks
import { useAgent } from "@/hooks/use-agents";
import { useThreads, useCreateThread } from "@/hooks/use-threads";
import { useMessages, useInvalidateMessages } from "@/hooks/use-messages";

// Import context providers
import {
  ThreadInputProvider,
  useThreadInput,
} from "@/contexts/ThreadInputContext";
import {
  AgentSettingsProvider,
  useAgentSettings,
} from "@/contexts/AgentSettingsContext";

// Import components
import { ThreadSidebar } from "@/components/agents/ThreadSidebar";
import { AgentInformation } from "@/components/agents/AgentInformation";
import { ResizeHandle } from "@/components/agents/ResizeHandle";

/**
 * Tool call interface for streaming
 */
interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  status: "pending" | "running" | "completed" | "error";
}

/**
 * Parse thinking content from message
 */
function parseThinking(content: string): {
  thinking: string | null;
  mainContent: string;
} {
  const thinkingMatch = content.match(/<thinking>([\s\S]*?)<\/thinking>/);
  const thinking = thinkingMatch ? thinkingMatch[1].trim() : null;
  const mainContent = content
    .replace(/<thinking>[\s\S]*?<\/thinking>/g, "")
    .trim();
  return { thinking, mainContent };
}

/**
 * Highlight tool names in text
 */
function highlightToolNames(text: string): string {
  return text.replace(
    /`?([a-zA-Z_][a-zA-Z0-9_]*(?:Tool|Scraper|Search|API))`?/g,
    '<span class="inline-block px-1.5 py-0.5 mx-0.5 rounded bg-[#252525] font-mono text-xs border border-[#444] text-white">$1</span>'
  );
}

/**
 * ToolCallDropdown - Collapsible tool call display
 */
function ToolCallDropdown({ toolCall }: { toolCall: ToolCall }) {
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
          toolCall.status === "running" && "animate-pulse",
          toolCall.status === "error" && "border-red-900 bg-red-950/20"
        )}
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        )}
        {toolCall.status === "error" ? (
          <AlertCircle className="h-3 w-3 text-red-500" />
        ) : (
          <Sparkles className="h-3 w-3 text-amber-500" />
        )}
        <span
          className={cn(
            "font-mono text-xs",
            toolCall.status === "error" ? "text-red-400" : "text-foreground"
          )}
        >
          {toolCall.name}
        </span>
        {toolCall.status === "running" && (
          <span className="text-xs text-muted-foreground ml-2">running...</span>
        )}
        {toolCall.status === "error" && (
          <span className="text-xs text-red-500 ml-2">failed</span>
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
              <pre
                className={cn(
                  "bg-[#0a0a0a] rounded-md p-3 text-xs font-mono overflow-x-auto max-h-64 border",
                  toolCall.status === "error"
                    ? "border-red-900 bg-red-950/10"
                    : "border-[#222]"
                )}
              >
                <code
                  className={cn(
                    toolCall.status === "error"
                      ? "text-red-400"
                      : "text-[#e6db74]"
                  )}
                >
                  {resultJson}
                </code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Collapsible thinking section - shows "Thought for Xs" when collapsed
 */
function ThinkingSection({
  thinking,
  toolCalls,
  isComplete,
  thinkingDuration,
}: {
  thinking: string | null;
  toolCalls: ToolCall[];
  isComplete: boolean;
  thinkingDuration: number;
}) {
  const [isExpanded, setIsExpanded] = useState(!isComplete);

  // Auto-collapse when thinking becomes complete
  useEffect(() => {
    if (isComplete) {
      setIsExpanded(false);
    }
  }, [isComplete]);

  const hasThinkingContent = thinking || toolCalls.length > 0;
  if (!hasThinkingContent) return null;

  const durationText =
    thinkingDuration > 0
      ? `Thought for ${Math.ceil(thinkingDuration / 1000)}s`
      : "Thinking...";

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          "flex items-center gap-2 text-sm transition-colors",
          "text-muted-foreground hover:text-foreground"
        )}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        <span>{isComplete ? durationText : "Thinking..."}</span>
      </button>

      {isExpanded && (
        <div className="mt-3 pl-6 border-l-2 border-[#333] space-y-3">
          {/* Thinking text */}
          {thinking && (
            <div className="text-foreground/70 text-sm">
              <span
                dangerouslySetInnerHTML={{
                  __html: highlightToolNames(thinking),
                }}
              />
            </div>
          )}

          {/* Tool Calls */}
          {toolCalls.length > 0 && (
            <div className="space-y-2">
              {toolCalls.map((tc) => (
                <ToolCallDropdown key={tc.id} toolCall={tc} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Message bubble component with collapsible thinking section
 */
function MessageBubble({
  message,
  isThinking = false,
  toolCalls = [],
  isComplete = true,
  thinkingDuration = 0,
}: {
  message: { id: string; role: string; content: string };
  isThinking?: boolean;
  toolCalls?: ToolCall[];
  isComplete?: boolean;
  thinkingDuration?: number;
}) {
  const isUser = message.role === "user";
  const { thinking, mainContent } = parseThinking(message.content);

  return (
    <div className={cn("flex gap-3", isUser && "justify-end")}>
      {!isUser && (
        <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-3",
          isUser ? "bg-primary text-primary-foreground" : "bg-transparent"
        )}
      >
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : isThinking && !message.content && toolCalls.length === 0 ? (
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-muted-foreground animate-pulse" />
            <div className="h-2 w-2 rounded-full bg-muted-foreground animate-pulse delay-75" />
            <div className="h-2 w-2 rounded-full bg-muted-foreground animate-pulse delay-150" />
            <span className="text-sm text-muted-foreground ml-2">
              Thinking...
            </span>
          </div>
        ) : (
          <div>
            {/* Collapsible Thinking Section */}
            {(thinking || toolCalls.length > 0) && (
              <ThinkingSection
                thinking={thinking}
                toolCalls={toolCalls}
                isComplete={isComplete}
                thinkingDuration={thinkingDuration}
              />
            )}

            {/* Main Content */}
            {mainContent && (
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{mainContent}</ReactMarkdown>
              </div>
            )}
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

/**
 * Chat content component (uses ThreadInput context)
 */
function ChatContent({
  agentId,
  threadId,
  onThreadCreated,
}: {
  agentId: string;
  threadId: string | null;
  onThreadCreated?: (threadId: string) => void;
}) {
  const { input, setInput, clearInput } = useThreadInput();
  const { settings } = useAgentSettings();
  const invalidateMessages = useInvalidateMessages();
  const createThreadMutation = useCreateThread(agentId);

  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [optimisticUserMessage, setOptimisticUserMessage] = useState<
    string | null
  >(null);
  const [streamingCompleted, setStreamingCompleted] = useState(false);
  const [streamingToolCalls, setStreamingToolCalls] = useState<ToolCall[]>([]);
  const [thinkingStartTime, setThinkingStartTime] = useState<number | null>(
    null
  );
  const [thinkingDuration, setThinkingDuration] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: messages } = useMessages(threadId || undefined);

  // Check if the last message is an assistant message (means it was saved to server)
  const lastMessage =
    messages && messages.length > 0 ? messages[messages.length - 1] : null;
  const lastMessageIsAssistant = lastMessage?.role === "assistant";

  // If streaming completed and we have an assistant message, hide streaming content
  const shouldHideStreamingContent =
    streamingCompleted && lastMessageIsAssistant;

  // Clear streaming content when assistant response is saved
  useEffect(() => {
    if (shouldHideStreamingContent && streamingContent) {
      // Clear streaming content immediately when we detect the message is saved
      setStreamingContent("");
      setIsStreaming(false);
      setIsThinking(false);
      setStreamingCompleted(false); // Reset for next message
      setStreamingToolCalls([]); // Clear tool calls too
    }
  }, [shouldHideStreamingContent, streamingContent]);

  // Reset state on thread change
  useEffect(() => {
    setStreamingContent("");
    setIsStreaming(false);
    setIsThinking(false);
    setStreamingCompleted(false);
    setStreamingToolCalls([]);
    setOptimisticUserMessage(null);
  }, [threadId]);

  // Clear optimistic user message when it appears in fetched messages
  useEffect(() => {
    if (optimisticUserMessage && messages) {
      const userMessageExists = messages.some(
        (msg) => msg.role === "user" && msg.content === optimisticUserMessage
      );
      if (userMessageExists) {
        setOptimisticUserMessage(null);
      }
    }
  }, [messages, optimisticUserMessage]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, isThinking, optimisticUserMessage]);

  const handleSend = async () => {
    if (!input.trim() || !agentId || isStreaming) return;

    const userMessage = input;
    let currentThreadId = threadId;

    // Show optimistic user message immediately
    setOptimisticUserMessage(userMessage);
    clearInput();

    // Create thread if it doesn't exist
    if (!currentThreadId) {
      const newThread = await createThreadMutation.mutateAsync({
        title: undefined,
        message: userMessage, // Pass message for auto-title generation
      });
      currentThreadId = newThread.id;
      onThreadCreated?.(currentThreadId);
    }

    setIsStreaming(true);
    setStreamingContent("");
    setIsThinking(false);
    setStreamingCompleted(false); // Reset streaming completed state

    // Invalidate messages to fetch latest (including the user message we just sent)
    invalidateMessages(currentThreadId);

    try {
      const request: GenerateRequest = {
        message: userMessage,
        thread_id: currentThreadId,
        temperature: settings.temperature,
        max_tokens: settings.maxTokens,
      };

      const streamEnabled = settings.stream ?? true;

      if (streamEnabled) {
        // Streaming mode
        setIsThinking(true);
        setStreamingToolCalls([]);
        setThinkingStartTime(Date.now());
        setThinkingDuration(0);
        let fullContent = "";

        for await (const event of streamAgentResponse(agentId, request)) {
          if (event.type === "thinking") {
            setIsThinking(true);
          } else if (event.type === "token") {
            setIsThinking(false);
            const content = (event.data as { content?: string }).content || "";
            fullContent += content;
            setStreamingContent(fullContent);
          } else if (event.type === "tool_start") {
            // Add new tool call with running status
            const data = event.data as {
              tool_name: string;
              tool_id: string;
              arguments: Record<string, unknown>;
            };
            setStreamingToolCalls((prev) => [
              ...prev,
              {
                id: data.tool_id,
                name: data.tool_name,
                arguments: data.arguments,
                status: "running",
              },
            ]);
          } else if (event.type === "tool_result") {
            // Update tool call with result
            const data = event.data as {
              tool_name: string;
              tool_id: string;
              result: unknown;
              success: boolean;
            };
            setStreamingToolCalls((prev) =>
              prev.map((tc) =>
                tc.id === data.tool_id
                  ? {
                      ...tc,
                      result: data.result,
                      status: data.success ? "completed" : "error",
                    }
                  : tc
              )
            );
          } else if (event.type === "done") {
            setIsThinking(false);
            setStreamingCompleted(true); // Mark streaming as completed
            // Calculate thinking duration
            if (thinkingStartTime) {
              setThinkingDuration(Date.now() - thinkingStartTime);
            }
            break;
          } else if (event.type === "error") {
            const error =
              (event.data as { error?: string }).error || "Unknown error";
            throw new Error(error);
          }
        }
      } else {
        // Generate mode (non-streaming)
        setIsThinking(true);
        const response = await generateAgentResponse(agentId, request);
        setStreamingContent(response.content);
        setIsThinking(false);
        setStreamingCompleted(true); // Mark as completed for non-streaming too
      }

      // Refresh messages after response completes to get the saved assistant message
      // This will trigger the useEffect that clears streamingContent
      invalidateMessages(currentThreadId);
    } catch (error) {
      console.error("Error:", error);
      setIsStreaming(false);
      setIsThinking(false);
      setStreamingContent(
        `Error: ${error instanceof Error ? error.message : "Unknown error"}`
      );
      // Clear error message after a delay
      setTimeout(() => {
        setStreamingContent("");
      }, 3000);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Messages - Only this area scrolls */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 min-h-0">
        {/* Show fetched messages */}
        {messages?.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Show optimistic user message if not yet in fetched messages */}
        {optimisticUserMessage && (
          <MessageBubble
            message={{
              id: "optimistic-user",
              role: "user",
              content: optimisticUserMessage,
            }}
          />
        )}

        {/* Show thinking indicator only if we're thinking and don't have streaming content yet */}
        {isThinking &&
          !streamingContent &&
          !shouldHideStreamingContent &&
          streamingToolCalls.length === 0 && (
            <MessageBubble
              message={{
                id: "thinking",
                role: "assistant",
                content: "",
              }}
              isThinking={true}
            />
          )}

        {/* Show streaming content or tool calls if we don't have the assistant response saved yet */}
        {(streamingContent || streamingToolCalls.length > 0) &&
          !shouldHideStreamingContent && (
            <MessageBubble
              message={{
                id: "streaming",
                role: "assistant",
                content: streamingContent,
              }}
              toolCalls={streamingToolCalls}
              isThinking={isThinking && !streamingContent}
              isComplete={streamingCompleted}
              thinkingDuration={thinkingDuration}
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
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Enter your message..."
            disabled={isStreaming}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
          />
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
  );
}

/**
 * Main AgentChatPage component
 * Uses providers for state management (following Mastra pattern)
 */
function AgentChatPageContent() {
  const { agentId, threadId: threadIdFromParams } = useParams<{
    agentId: string;
    threadId?: string;
  }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const threadIdFromQuery = searchParams.get("threadId");

  // Prefer URL param, then query param, then null
  const threadIdFromUrl = threadIdFromParams || threadIdFromQuery || null;

  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(
    threadIdFromUrl
  );
  const [activeTab, setActiveTab] = useState<"chat" | "traces" | "evals">(
    "chat"
  );
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);
  const [mobileThreadsOpen, setMobileThreadsOpen] = useState(false);
  const [mobileInfoOpen, setMobileInfoOpen] = useState(false);

  // Fetch agent
  const { data: agent, isLoading: agentLoading } = useAgent(agentId);

  // Fetch threads
  const { data: threads } = useThreads(agentId);

  // Sync selectedThreadId with URL
  useEffect(() => {
    if (threadIdFromUrl && threadIdFromUrl !== selectedThreadId) {
      setSelectedThreadId(threadIdFromUrl);
    }
  }, [threadIdFromUrl, selectedThreadId]);

  // Auto-select first thread if none selected and threads exist
  useEffect(() => {
    if (threads && threads.length > 0 && !selectedThreadId) {
      const firstThread = threads[0];
      setSelectedThreadId(firstThread.id);
      setSearchParams({ threadId: firstThread.id });
    }
  }, [threads, selectedThreadId, setSearchParams]);

  // Handle thread selection
  const handleThreadSelect = (threadId: string) => {
    setSelectedThreadId(threadId);
    setSearchParams({ threadId });
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
    <AgentSettingsProvider
      agentId={agentId!}
      defaultSettings={{ stream: true }}
    >
      <ThreadInputProvider>
        <div className="flex h-full relative">
          {/* Mobile Threads Sidebar Overlay */}
          {mobileThreadsOpen && (
            <div
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              onClick={() => setMobileThreadsOpen(false)}
            />
          )}

          {/* Thread Sidebar - Desktop: collapsible, Mobile: overlay */}
          <div
            className={cn(
              "md:relative fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 ease-in-out md:transform-none",
              mobileThreadsOpen
                ? "translate-x-0"
                : "-translate-x-full md:translate-x-0",
              leftSidebarCollapsed && "md:hidden"
            )}
          >
            <ThreadSidebar
              agentId={agentId!}
              agentName={agent.name}
              selectedThreadId={selectedThreadId}
              onThreadSelect={(threadId) => {
                handleThreadSelect(threadId);
                setMobileThreadsOpen(false); // Close mobile menu after selection
              }}
              isCollapsed={false} // Always show when visible
              onToggle={() => {
                setLeftSidebarCollapsed(true);
                setMobileThreadsOpen(false);
              }}
            />
          </div>

          {/* Left Resize Handle - Desktop only */}
          {!leftSidebarCollapsed && (
            <div className="hidden md:block">
              <ResizeHandle
                side="left"
                isCollapsed={leftSidebarCollapsed}
                onToggle={() => setLeftSidebarCollapsed(true)}
                className="w-1"
              />
            </div>
          )}

          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            {/* Header with Tabs */}
            <header className="flex items-center justify-between border-b border-border px-2 md:px-4 py-2">
              <div className="flex items-center gap-2 md:gap-4">
                {/* Mobile: Threads Menu Button */}
                <button
                  onClick={() => setMobileThreadsOpen(true)}
                  className="md:hidden p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                  title="Show threads"
                >
                  <Menu className="h-4 w-4" />
                </button>

                {/* Desktop: Toggle Left Sidebar Button */}
                {leftSidebarCollapsed && (
                  <button
                    onClick={() => setLeftSidebarCollapsed(false)}
                    className="hidden md:flex p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                    title="Show threads"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                )}

                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4" />
                  <span className="font-medium text-sm md:text-base truncate">
                    {agent.name}
                  </span>
                </div>

                {/* Tabs - Hide on very small screens */}
                <nav className="hidden sm:flex gap-2 md:gap-4">
                  {(["chat", "traces", "evals"] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={cn(
                        "text-xs md:text-sm capitalize transition-colors px-2 py-1 rounded",
                        activeTab === tab
                          ? "text-foreground bg-secondary"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                      )}
                    >
                      {tab}
                    </button>
                  ))}
                </nav>
              </div>
              <div className="flex items-center gap-1 md:gap-2">
                {/* Mobile: Info Menu Button */}
                <button
                  onClick={() => setMobileInfoOpen(true)}
                  className="lg:hidden p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                  title="Show agent info"
                >
                  <Menu className="h-4 w-4 rotate-90" />
                </button>

                {/* Desktop: Toggle Right Sidebar Button */}
                {rightSidebarCollapsed && (
                  <button
                    onClick={() => setRightSidebarCollapsed(false)}
                    className="hidden lg:flex p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                    title="Show agent info"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                )}
                {/* Stream/Generate Toggle */}
                <StreamModeToggle />
              </div>
            </header>

            {/* Chat Content */}
            <div className="flex flex-1 overflow-hidden relative min-h-0">
              <ChatContent
                agentId={agentId!}
                threadId={selectedThreadId}
                onThreadCreated={handleThreadSelect}
              />

              {/* Mobile Info Sidebar Overlay */}
              {mobileInfoOpen && (
                <div
                  className="fixed inset-0 z-40 bg-black/50 lg:hidden"
                  onClick={() => setMobileInfoOpen(false)}
                />
              )}

              {/* Right Resize Handle - Desktop only */}
              {!rightSidebarCollapsed && (
                <div className="hidden lg:block">
                  <ResizeHandle
                    side="right"
                    isCollapsed={rightSidebarCollapsed}
                    onToggle={() => setRightSidebarCollapsed(true)}
                    className="w-1"
                  />
                </div>
              )}

              {/* Agent Information - Desktop: collapsible, Mobile: overlay */}
              <div
                className={cn(
                  "lg:relative fixed inset-y-0 right-0 z-50 transform transition-transform duration-300 ease-in-out lg:transform-none",
                  mobileInfoOpen
                    ? "translate-x-0"
                    : "translate-x-full lg:translate-x-0",
                  rightSidebarCollapsed && "lg:hidden"
                )}
              >
                <AgentInformation
                  agent={agent}
                  agentId={agentId!}
                  isCollapsed={false} // Always show when visible
                  onToggle={() => {
                    setRightSidebarCollapsed(true);
                    setMobileInfoOpen(false);
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </ThreadInputProvider>
    </AgentSettingsProvider>
  );
}

/**
 * Stream/Generate mode toggle component
 */
function StreamModeToggle() {
  const { settings, updateSettings } = useAgentSettings();
  const streamMode = settings.stream ?? true;

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">Mode:</span>
      <button
        onClick={() => updateSettings({ stream: !streamMode })}
        className={cn(
          "flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition-colors",
          streamMode
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-muted-foreground hover:bg-secondary/80"
        )}
      >
        {streamMode ? (
          <>
            <Zap className="h-3 w-3" /> Stream
          </>
        ) : (
          <>
            <Sparkles className="h-3 w-3" /> Generate
          </>
        )}
      </button>
    </div>
  );
}

/**
 * Exported component with providers
 */
export function AgentChatPage() {
  return <AgentChatPageContent />;
}
