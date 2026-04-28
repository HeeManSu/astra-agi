import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { Message, SessionKey, ToolCall } from "@/types/domain";
import type { ThreadMessage } from "@/types/api";

export interface ChatState {
  messagesBySession: Record<string, Message[]>;
  currentSession: SessionKey | null;
  isStreaming: boolean;
  streamingContent: string;
  inputValue: string;
}

const initialState: ChatState = {
  messagesBySession: {},
  currentSession: null,
  isStreaming: false,
  streamingContent: "",
  inputValue: "",
};

interface PersistedToolCallShape {
  name?: string;
  result?: unknown;
}

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    setCurrentSession: (state, action: PayloadAction<SessionKey | null>) => {
      state.currentSession = action.payload;
      if (action.payload && !state.messagesBySession[action.payload]) {
        state.messagesBySession[action.payload] = [];
      }
    },
    addMessage: (
      state,
      action: PayloadAction<{
        sessionKey: SessionKey;
        message: Partial<Message> &
          Pick<Message, "role" | "content"> & { id?: string };
      }>,
    ) => {
      const { sessionKey, message } = action.payload;
      if (!state.messagesBySession[sessionKey]) {
        state.messagesBySession[sessionKey] = [];
      }
      state.messagesBySession[sessionKey].push({
        ...message,
        id: message.id ?? crypto.randomUUID(),
        timestamp: message.timestamp ?? new Date().toISOString(),
      });
    },
    updateLastMessage: (
      state,
      action: PayloadAction<{ sessionKey: SessionKey; content: string }>,
    ) => {
      const { sessionKey, content } = action.payload;
      const messages = state.messagesBySession[sessionKey];
      if (messages && messages.length > 0) {
        const last = messages[messages.length - 1];
        if (last && last.role === "assistant") {
          last.content = content;
        }
      }
    },
    updateToolCall: (
      state,
      action: PayloadAction<{ sessionKey: SessionKey; toolCall: ToolCall }>,
    ) => {
      const { sessionKey, toolCall } = action.payload;
      const messages = state.messagesBySession[sessionKey];
      if (!messages || messages.length === 0) return;
      const last = messages[messages.length - 1];
      if (!last || last.role !== "assistant") return;

      if (!last.tool_calls) last.tool_calls = [];
      const existing = last.tool_calls.findIndex(
        (tc) => tc.index === toolCall.index,
      );
      if (existing !== -1) {
        last.tool_calls[existing] = { ...last.tool_calls[existing], ...toolCall };
      } else {
        last.tool_calls.push(toolCall);
      }
    },
    setStreaming: (state, action: PayloadAction<boolean>) => {
      state.isStreaming = action.payload;
    },
    appendStreamingContent: (state, action: PayloadAction<string>) => {
      state.streamingContent += action.payload;
    },
    clearStreamingContent: (state) => {
      state.streamingContent = "";
    },
    setInputValue: (state, action: PayloadAction<string>) => {
      state.inputValue = action.payload;
    },
    setMessages: (
      state,
      action: PayloadAction<{
        sessionKey: SessionKey;
        messages: ThreadMessage[];
      }>,
    ) => {
      const { sessionKey, messages } = action.payload;
      state.messagesBySession[sessionKey] = messages.map((msg) => {
        const meta = msg.metadata;
        const persisted =
          meta && typeof meta === "object" && "tool_calls" in meta
            ? (meta.tool_calls as PersistedToolCallShape[] | undefined)
            : undefined;

        const tool_calls: ToolCall[] | undefined =
          persisted && persisted.length > 0
            ? persisted.map((tc, idx) => ({
                index: idx,
                tool_name: tc.name ?? "Unknown Tool",
                result: tc.result,
                status: "complete" as const,
              }))
            : undefined;

        return {
          id: msg.id || crypto.randomUUID(),
          role: msg.role,
          content: msg.content,
          timestamp: msg.created_at || new Date().toISOString(),
          ...(tool_calls ? { tool_calls } : {}),
          ...(msg.metadata ? { metadata: msg.metadata } : {}),
        };
      });
    },
    clearSession: (state, action: PayloadAction<SessionKey>) => {
      const sessionKey = action.payload;
      if (state.messagesBySession[sessionKey]) {
        state.messagesBySession[sessionKey] = [];
      }
    },
  },
});

export const {
  setCurrentSession,
  addMessage,
  updateLastMessage,
  updateToolCall,
  setStreaming,
  appendStreamingContent,
  clearStreamingContent,
  setInputValue,
  setMessages,
  clearSession,
} = chatSlice.actions;

export const selectCurrentMessages = (state: {
  chat: ChatState;
}): Message[] => {
  const sessionKey = state.chat.currentSession;
  return sessionKey ? (state.chat.messagesBySession[sessionKey] ?? []) : [];
};

export default chatSlice.reducer;
