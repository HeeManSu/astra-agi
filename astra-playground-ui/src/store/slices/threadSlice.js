import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import {
  getThreads,
  createThread,
  getThreadMessages,
  deleteThread,
} from "../../api/client";

// Async thunks
export const fetchThreads = createAsyncThunk(
  "threads/fetchThreads",
  async (
    { serverUrl, apiKey, resourceType, resourceId },
    { rejectWithValue }
  ) => {
    try {
      return await getThreads(serverUrl, apiKey, resourceType, resourceId);
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const createNewThread = createAsyncThunk(
  "threads/createThread",
  async ({ serverUrl, apiKey, data }, { rejectWithValue }) => {
    try {
      return await createThread(serverUrl, apiKey, data);
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const fetchThreadMessages = createAsyncThunk(
  "threads/fetchMessages",
  async ({ serverUrl, apiKey, threadId }, { rejectWithValue }) => {
    try {
      return await getThreadMessages(serverUrl, apiKey, threadId);
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const removeThread = createAsyncThunk(
  "threads/deleteThread",
  async ({ serverUrl, apiKey, threadId }, { rejectWithValue }) => {
    try {
      await deleteThread(serverUrl, apiKey, threadId);
      return threadId;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

const initialState = {
  // Thread list
  threads: [],
  isLoading: false,
  error: null,

  // Current thread
  currentThreadId: null,

  // Resource context
  currentResource: null, // { type: "agent"|"team", id: string, name: string }
};

const threadSlice = createSlice({
  name: "threads",
  initialState,
  reducers: {
    setCurrentThread: (state, action) => {
      state.currentThreadId = action.payload;
    },
    setCurrentResource: (state, action) => {
      // { type, id, name }
      state.currentResource = action.payload;
      // Clear threads when switching resources
      state.threads = [];
      state.currentThreadId = null;
    },
    clearThreads: (state) => {
      state.threads = [];
      state.currentThreadId = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch threads
    builder.addCase(fetchThreads.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(fetchThreads.fulfilled, (state, action) => {
      state.isLoading = false;
      state.threads = action.payload;
    });
    builder.addCase(fetchThreads.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
    });

    // Create thread
    builder.addCase(createNewThread.fulfilled, (state, action) => {
      state.threads.unshift(action.payload); // Add to top
      state.currentThreadId = action.payload.id;
    });

    // Delete thread
    builder.addCase(removeThread.fulfilled, (state, action) => {
      state.threads = state.threads.filter((t) => t.id !== action.payload);
      if (state.currentThreadId === action.payload) {
        state.currentThreadId = null;
      }
    });
  },
});

export const { setCurrentThread, setCurrentResource, clearThreads } =
  threadSlice.actions;

// Selectors
export const selectThreads = (state) => state.threads.threads;
export const selectCurrentThreadId = (state) => state.threads.currentThreadId;
export const selectCurrentThread = (state) =>
  state.threads.threads.find((t) => t.id === state.threads.currentThreadId);
export const selectIsLoading = (state) => state.threads.isLoading;
export const selectCurrentResource = (state) => state.threads.currentResource;

export default threadSlice.reducer;
