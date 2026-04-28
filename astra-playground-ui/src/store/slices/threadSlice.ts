import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

/**
 * UI-only thread state. Server data (the threads list itself, message history)
 * lives in the RTK Query cache (`@/api/rtkApi`); this slice tracks which
 * thread is selected.
 */

export interface ThreadState {
  currentThreadId: string | null;
}

const initialState: ThreadState = {
  currentThreadId: null,
};

const threadSlice = createSlice({
  name: "threads",
  initialState,
  reducers: {
    setCurrentThread: (state, action: PayloadAction<string | null>) => {
      state.currentThreadId = action.payload;
    },
  },
});

export const { setCurrentThread } = threadSlice.actions;

export const selectCurrentThreadId = (state: {
  threads: ThreadState;
}): string | null => state.threads.currentThreadId;

export default threadSlice.reducer;
