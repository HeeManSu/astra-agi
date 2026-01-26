import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { getTraces, getTraceDetail } from "@/api/telemetry";

// Async thunks
export const fetchTraces = createAsyncThunk(
  "telemetry/fetchTraces",
  async ({ serverUrl, apiKey, limit, offset }, { rejectWithValue }) => {
    try {
      return await getTraces(serverUrl, apiKey, limit, offset);
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

export const fetchTraceDetail = createAsyncThunk(
  "telemetry/fetchTraceDetail",
  async ({ serverUrl, apiKey, traceId }, { rejectWithValue }) => {
    try {
      return await getTraceDetail(serverUrl, apiKey, traceId);
    } catch (error) {
      return rejectWithValue(error.message);
    }
  },
);

const initialState = {
  traces: [],
  totalTraces: 0,
  selectedTrace: null,
  selectedTraceSpans: [],
  isLoading: false,
  isLoadingDetail: false,
  error: null,
  filters: {
    limit: 50,
    offset: 0,
  },
};

const telemetrySlice = createSlice({
  name: "telemetry",
  initialState,
  reducers: {
    clearSelection: (state) => {
      state.selectedTrace = null;
      state.selectedTraceSpans = [];
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    resetTelemetry: () => initialState,
  },
  extraReducers: (builder) => {
    // List Traces
    builder
      .addCase(fetchTraces.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchTraces.fulfilled, (state, action) => {
        state.isLoading = false;
        state.traces = action.payload.traces;
        state.totalTraces = action.payload.count;
      })
      .addCase(fetchTraces.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });

    // Trace Detail
    builder
      .addCase(fetchTraceDetail.pending, (state) => {
        state.isLoadingDetail = true;
        state.error = null;
      })
      .addCase(fetchTraceDetail.fulfilled, (state, action) => {
        state.isLoadingDetail = false;
        state.selectedTrace = action.payload.trace;
        state.selectedTraceSpans = action.payload.spans;

        // Also update the trace in the list to keep them in sync
        const traceIndex = state.traces.findIndex(
          (t) => t.trace_id === action.payload.trace.trace_id,
        );
        if (traceIndex !== -1) {
          state.traces[traceIndex] = action.payload.trace;
        }
      })
      .addCase(fetchTraceDetail.rejected, (state, action) => {
        state.isLoadingDetail = false;
        state.error = action.payload;
      });
  },
});

export const { clearSelection, setFilters, resetTelemetry } =
  telemetrySlice.actions;

export default telemetrySlice.reducer;
