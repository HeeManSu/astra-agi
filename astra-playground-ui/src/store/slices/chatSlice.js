import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  // Messages by session key (e.g., "agent:my-agent" or "team:my-team")
  messagesBySession: {},

  // Current session
  currentSession: null,

  // Streaming state
  isStreaming: false,
  streamingContent: "",

  // Input
  inputValue: "",
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    setCurrentSession: (state, action) => {
      state.currentSession = action.payload;
      // Initialize messages array for new session
      if (action.payload && !state.messagesBySession[action.payload]) {
        state.messagesBySession[action.payload] = [];
      }
    },
    addMessage: (state, action) => {
      const { sessionKey, message } = action.payload;
      if (!state.messagesBySession[sessionKey]) {
        state.messagesBySession[sessionKey] = [];
      }
      state.messagesBySession[sessionKey].push({
        ...message,
        id: message.id || crypto.randomUUID(),
        timestamp: message.timestamp || new Date().toISOString(),
      });
    },
    updateLastMessage: (state, action) => {
      const { sessionKey, content } = action.payload;
      const messages = state.messagesBySession[sessionKey];
      if (messages && messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        if (lastMessage.role === "assistant") {
          lastMessage.content = content;
        }
      }
    },
    updateToolCall: (state, action) => {
      const { sessionKey, toolCall } = action.payload;
      const messages = state.messagesBySession[sessionKey];
      if (messages && messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        if (lastMessage.role === "assistant") {
          if (!lastMessage.tool_calls) {
            lastMessage.tool_calls = [];
          }

          // Check if we're updating an existing tool call (by index)
          const existingIndex = lastMessage.tool_calls.findIndex(
            (tc) => tc.index === toolCall.index
          );

          if (existingIndex !== -1) {
            // Merge updates
            lastMessage.tool_calls[existingIndex] = {
              ...lastMessage.tool_calls[existingIndex],
              ...toolCall,
            };
          } else {
            // Add new tool call
            lastMessage.tool_calls.push(toolCall);
          }
        }
      }
    },
    setStreaming: (state, action) => {
      state.isStreaming = action.payload;
    },
    setStreamingContent: (state, action) => {
      state.streamingContent = action.payload;
    },
    appendStreamingContent: (state, action) => {
      state.streamingContent += action.payload;
    },
    clearStreamingContent: (state) => {
      state.streamingContent = "";
    },
    setInputValue: (state, action) => {
      state.inputValue = action.payload;
    },
    setMessages: (state, action) => {
      // Set messages for a session (used when loading thread history)
      const { sessionKey, messages } = action.payload;
      state.messagesBySession[sessionKey] = messages.map((msg) => ({
        ...msg,
        id: msg.id || crypto.randomUUID(),
        timestamp: msg.created_at || new Date().toISOString(),
      }));
    },
    clearSession: (state, action) => {
      const sessionKey = action.payload;
      if (state.messagesBySession[sessionKey]) {
        state.messagesBySession[sessionKey] = [];
      }
    },
    clearAllMessages: (state) => {
      state.messagesBySession = {};
    },
  },
});

export const {
  setCurrentSession,
  addMessage,
  updateLastMessage,
  updateToolCall,
  setStreaming,
  setStreamingContent,
  appendStreamingContent,
  clearStreamingContent,
  setInputValue,
  setMessages,
  clearSession,
  clearAllMessages,
} = chatSlice.actions;

// Selectors
export const selectCurrentMessages = (state) => {
  const sessionKey = state.chat.currentSession;
  return sessionKey ? state.chat.messagesBySession[sessionKey] || [] : [];
};

export default chatSlice.reducer;
