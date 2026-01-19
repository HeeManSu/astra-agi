import { useState, useRef, useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  addMessage,
  setStreaming,
  setStreamingContent,
  appendStreamingContent,
  clearStreamingContent,
  updateLastMessage,
  updateToolCall,
  setInputValue,
  selectCurrentMessages,
} from "@/store/slices/chatSlice";
import { streamAgent, streamTeam, runAgent, runTeam } from "@/api/client";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Send, Bot, User, Loader2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import Markdown from "react-markdown";

function ChatArea() {
  const dispatch = useAppDispatch();
  const { serverUrl, apiKey, selectedItem } = useAppSelector(
    (state) => state.app
  );
  const { currentSession, isStreaming, streamingContent, inputValue } =
    useAppSelector((state) => state.chat);
  const messages = useAppSelector(selectCurrentMessages);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // Stream mode toggle (true = streaming, false = non-streaming)
  const [streamMode, setStreamMode] = useState(true);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, [selectedItem]);

  const handleSend = async () => {
    if (!inputValue.trim() || isStreaming || !selectedItem) return;

    const userMessage = inputValue.trim();
    dispatch(setInputValue(""));

    // Add user message
    dispatch(
      addMessage({
        sessionKey: currentSession,
        message: { role: "user", content: userMessage },
      })
    );

    // Add placeholder assistant message
    dispatch(
      addMessage({
        sessionKey: currentSession,
        message: { role: "assistant", content: "" },
      })
    );

    dispatch(setStreaming(true));
    dispatch(clearStreamingContent());

    let fullContent = "";

    const onChunk = (event) => {
      // Handle different event types from streaming
      // Backend uses "event_type" field
      let content = "";

      if (event.event_type === "content" && event.data?.text) {
        content = event.data.text;
      } else if (event.event_type === "tool_call") {
        // Handle tool call start
        dispatch(
          updateToolCall({
            sessionKey: currentSession,
            toolCall: {
              ...event.data,
              status: "running",
            },
          })
        );
      } else if (event.event_type === "tool_result") {
        // Handle tool result
        dispatch(
          updateToolCall({
            sessionKey: currentSession,
            toolCall: {
              ...event.data,
              status: "complete",
            },
          })
        );
      } else if (event.event_type === "synthesize" && event.data?.message) {
        content = event.data.message;
      } else if (event.type === "content" && event.content) {
        // Fallback for agent streaming format
        content = event.content;
      } else if (event.delta?.content) {
        content = event.delta.content;
      } else if (typeof event === "string") {
        content = event;
      }

      if (content) {
        fullContent += content;
        dispatch(appendStreamingContent(content));
        dispatch(
          updateLastMessage({
            sessionKey: currentSession,
            content: fullContent,
          })
        );
      }
    };

    const onDone = () => {
      dispatch(setStreaming(false));
      dispatch(clearStreamingContent());
    };

    const onError = (error) => {
      console.error("Streaming error:", error);
      dispatch(
        updateLastMessage({
          sessionKey: currentSession,
          content: `Error: ${error.message}`,
        })
      );
      dispatch(setStreaming(false));
      dispatch(clearStreamingContent());
    };

    try {
      // Extract thread_id from session key (format: "thread:threadId")
      const threadId = currentSession?.startsWith("thread:")
        ? currentSession.replace("thread:", "")
        : null;

      if (streamMode) {
        // Streaming mode
        if (selectedItem.type === "agent") {
          await streamAgent(
            serverUrl,
            apiKey,
            selectedItem.id,
            userMessage,
            onChunk,
            onDone,
            onError,
            threadId
          );
        } else if (selectedItem.type === "team") {
          await streamTeam(
            serverUrl,
            apiKey,
            selectedItem.id,
            userMessage,
            onChunk,
            onDone,
            onError,
            threadId
          );
        }
      } else {
        // Non-streaming mode (invoke)
        let response;
        if (selectedItem.type === "agent") {
          response = await runAgent(
            serverUrl,
            apiKey,
            selectedItem.id,
            userMessage,
            threadId
          );
        } else if (selectedItem.type === "team") {
          response = await runTeam(
            serverUrl,
            apiKey,
            selectedItem.id,
            userMessage,
            threadId
          );
        }

        // Handle non-streaming response
        const content =
          response?.response || response?.content || JSON.stringify(response);
        dispatch(
          updateLastMessage({
            sessionKey: currentSession,
            content: content,
          })
        );
        dispatch(setStreaming(false));
      }
    } catch (error) {
      onError(error);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // No item selected
  if (!selectedItem) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background">
        <div className="text-center">
          <img
            src="/logo.svg"
            alt="Astra Logo"
            className="h-16 w-16 mx-auto invert"
          />
          <h2 className="mt-4 text-xl font-semibold text-foreground">
            Welcome to Astra Playground
          </h2>
          <p className="mt-2 text-muted-foreground">
            Select an agent or team from the sidebar to start chatting
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-background">
      {/* Header - Stream Toggle Only */}
      <div className="h-14 border-b border-border flex items-center justify-end px-4">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Invoke</span>
          <Switch
            checked={streamMode}
            onCheckedChange={setStreamMode}
            className="data-[state=checked]:bg-primary"
          />
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Zap className="h-3 w-3" />
            Stream
          </span>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">How can I help you today?</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={message.id || index}
                className={cn(
                  "flex gap-3 message-fade-in",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {message.role === "assistant" && (
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}

                <div
                  className={cn(
                    "max-w-[80%] rounded-lg px-4 py-2 text-sm",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  )}
                >
                  {/* Tool Calls Rendering */}
                  {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="mb-3 space-y-2">
                      {message.tool_calls.map((tool, idx) => (
                        <div
                          key={idx}
                          className="bg-background/50 rounded p-2 text-xs border border-border"
                        >
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
                          {tool.result && (
                            <div className="pl-4 border-l-2 border-border/50 mt-1 max-h-20 overflow-y-auto text-muted-foreground/80">
                              {typeof tool.result === "string"
                                ? tool.result
                                : JSON.stringify(tool.result)}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {message.content ? (
                    <div className="prose">
                      <Markdown>{message.content}</Markdown>
                    </div>
                  ) : (
                    <span className="text-muted-foreground">Thinking...</span>
                  )}
                  {isStreaming &&
                    index === messages.length - 1 &&
                    message.role === "assistant" && (
                      <span className="streaming-cursor" />
                    )}
                </div>

                {message.role === "user" && (
                  <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-border p-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => dispatch(setInputValue(e.target.value))}
                onKeyDown={handleKeyDown}
                placeholder="Enter your message..."
                rows={1}
                className="w-full resize-none rounded-lg border border-input bg-background px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                style={{ minHeight: "48px", maxHeight: "200px" }}
                disabled={isStreaming}
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={!inputValue.trim() || isStreaming}
              size="icon"
              className="h-12 w-12"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatArea;
