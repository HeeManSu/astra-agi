/**
 * Owns the SSE read loop and the invoke fallback. Returns a single `send`
 * function that the composer calls; the hook handles thread creation, the
 * stream-vs-invoke branching, and dispatches Redux updates as content arrives.
 */

import { useCallback } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  addMessage,
  appendStreamingContent,
  clearStreamingContent,
  setCurrentSession,
  setStreaming,
  updateLastMessage,
  updateToolCall,
} from "@/store/slices/chatSlice";
import {
  createThread,
  runAgent,
  runTeam,
  streamAgent,
  streamTeam,
} from "@/api/client";
import type { SessionKey, ToolCall } from "@/types/domain";
import type { StreamEvent } from "@/types/sse";

interface SendOptions {
  text: string;
  streamMode: boolean;
}

export function useChatStream() {
  const dispatch = useAppDispatch();
  const { serverUrl, apiKey, selectedItem } = useAppSelector(
    (state) => state.app,
  );
  const currentSession = useAppSelector((state) => state.chat.currentSession);

  const send = useCallback(
    async ({ text, streamMode }: SendOptions): Promise<void> => {
      if (!text.trim() || !selectedItem || !currentSession) return;

      const sessionKey: SessionKey = currentSession;
      const userMessage = text.trim();

      dispatch(
        addMessage({
          sessionKey,
          message: { role: "user", content: userMessage },
        }),
      );
      dispatch(
        addMessage({
          sessionKey,
          message: { role: "assistant", content: "" },
        }),
      );

      dispatch(setStreaming(true));
      dispatch(clearStreamingContent());

      let fullContent = "";

      const onChunk = (event: StreamEvent): void => {
        let content = "";

        if ("event_type" in event) {
          if (event.event_type === "content") {
            content = event.data.text;
          } else if (event.event_type === "tool_call") {
            const toolCall: ToolCall = { ...event.data, status: "running" };
            dispatch(updateToolCall({ sessionKey, toolCall }));
          } else if (event.event_type === "tool_result") {
            const toolCall: ToolCall = {
              index: event.data.index,
              tool_name: event.data.tool_name ?? "",
              result: event.data.result,
              status: "complete",
            };
            dispatch(updateToolCall({ sessionKey, toolCall }));
          } else if (event.event_type === "synthesize") {
            content = event.data.message;
          }
        } else if ("type" in event && event.type === "content") {
          content = event.content;
        } else if ("delta" in event) {
          content = event.delta.content;
        }

        if (content) {
          fullContent += content;
          dispatch(appendStreamingContent(content));
          dispatch(updateLastMessage({ sessionKey, content: fullContent }));
        }
      };

      const onDone = (): void => {
        dispatch(setStreaming(false));
        dispatch(clearStreamingContent());
      };

      const onError = (error: Error): void => {
        console.error("Streaming error:", error);
        dispatch(
          updateLastMessage({
            sessionKey,
            content: `Error: ${error.message}`,
          }),
        );
        dispatch(setStreaming(false));
        dispatch(clearStreamingContent());
      };

      try {
        let threadId: string | null = null;
        if (sessionKey.startsWith("thread:")) {
          threadId = sessionKey.replace("thread:", "");
        } else {
          try {
            const resourceName =
              typeof selectedItem.data?.name === "string"
                ? selectedItem.data.name
                : selectedItem.id;
            const thread = await createThread(serverUrl, apiKey, {
              resource_type: selectedItem.type,
              resource_id: selectedItem.id,
              resource_name: resourceName,
              title:
                userMessage.slice(0, 50) +
                (userMessage.length > 50 ? "..." : ""),
            });
            threadId = thread.id;
            dispatch(setCurrentSession(`thread:${threadId}`));
          } catch (err) {
            console.error("Failed to create thread:", err);
          }
        }

        if (streamMode) {
          const stream = selectedItem.type === "agent" ? streamAgent : streamTeam;
          await stream(
            serverUrl,
            apiKey,
            selectedItem.id,
            userMessage,
            onChunk,
            onDone,
            onError,
            threadId,
          );
        } else {
          const invoke = selectedItem.type === "agent" ? runAgent : runTeam;
          const response = await invoke(
            serverUrl,
            apiKey,
            selectedItem.id,
            userMessage,
            threadId,
          );
          const content = response.response || JSON.stringify(response);
          dispatch(updateLastMessage({ sessionKey, content }));
          dispatch(setStreaming(false));
        }
      } catch (error) {
        onError(error instanceof Error ? error : new Error(String(error)));
      }
    },
    [dispatch, serverUrl, apiKey, selectedItem, currentSession],
  );

  return { send };
}
