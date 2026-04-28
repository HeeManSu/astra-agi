import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

/**
 * UI-only telemetry state. The actual traces/spans/logs live in the RTK Query
 * cache (`@/api/rtkApi`); this slice tracks which trace the user has clicked
 * on so that TraceDetail can subscribe to it.
 */

export interface TelemetryState {
  selectedTraceId: string | null;
}

const initialState: TelemetryState = {
  selectedTraceId: null,
};

const telemetrySlice = createSlice({
  name: "telemetry",
  initialState,
  reducers: {
    selectTrace: (state, action: PayloadAction<string | null>) => {
      state.selectedTraceId = action.payload;
    },
  },
});

export const { selectTrace } = telemetrySlice.actions;

export default telemetrySlice.reducer;
