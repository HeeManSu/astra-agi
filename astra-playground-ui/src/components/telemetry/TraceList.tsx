import { useState } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectTrace } from "@/store/slices/telemetrySlice";
import {
  useGetTraceListQuery,
  useGetTraceDetailQuery,
} from "@/api/rtkApi";
import { skipToken } from "@reduxjs/toolkit/query/react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  Clock,
  Activity,
  Search,
  RefreshCw,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import type { Trace, TraceStatus } from "@/types/api";

const STATUS_DOT_COLORS: Record<TraceStatus, string> = {
  SUCCESS: "bg-emerald-400",
  ERROR: "bg-red-400",
  RUNNING: "bg-amber-400 animate-pulse",
};

type StatusFilter = "ALL" | TraceStatus;
const STATUS_FILTERS: StatusFilter[] = ["ALL", "SUCCESS", "ERROR", "RUNNING"];

function formatDuration(ms: number | null): string {
  if (ms == null) return "Running...";
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export default function TraceList() {
  const dispatch = useAppDispatch();
  const { serverUrl } = useAppSelector((state) => state.app);
  const selectedTraceId = useAppSelector(
    (state) => state.telemetry.selectedTraceId,
  );
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");

  const {
    data: traceData,
    isLoading,
    refetch,
  } = useGetTraceListQuery(serverUrl ? { limit: 50, offset: 0 } : skipToken, {
    pollingInterval: 10000,
  });
  const traces = traceData?.traces ?? [];

  // Subscribed to keep list status in sync with detail when one is selected
  const { data: selectedDetail } = useGetTraceDetailQuery(
    selectedTraceId ?? skipToken,
  );

  const handleSelectTrace = (traceId: string) => {
    dispatch(selectTrace(traceId));
  };

  const handleRefresh = () => {
    if (serverUrl) void refetch();
  };

  const filteredTraces = traces.filter((trace) => {
    const matchesSearch =
      searchTerm === "" ||
      trace.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus =
      statusFilter === "ALL" || trace.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getDisplayStatus = (trace: Trace): TraceStatus => {
    if (selectedDetail && selectedDetail.trace.trace_id === trace.trace_id) {
      return selectedDetail.trace.status;
    }
    return trace.status;
  };

  const getStatusDot = (status: TraceStatus) => (
    <span
      className={cn(
        "w-2.5 h-2.5 rounded-full shrink-0",
        STATUS_DOT_COLORS[status] || "bg-gray-400",
      )}
    />
  );

  return (
    <div className="h-full flex flex-col border-r border-border bg-card/50">
      <div className="p-4 border-b border-border bg-muted/30">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-lg flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            Traces
          </h2>
          <button
            onClick={handleRefresh}
            className="p-1.5 hover:bg-muted rounded-md transition-colors"
            title="Refresh"
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </button>
        </div>

        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search traces..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 h-9 bg-background"
          />
        </div>

        <div className="flex gap-1">
          {STATUS_FILTERS.map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                "px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
                statusFilter === status
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted hover:bg-muted/80 text-muted-foreground",
              )}
            >
              {status === "ALL"
                ? "All"
                : status.charAt(0) + status.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>

      {isLoading && traces.length === 0 && (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <RefreshCw className="h-5 w-5 animate-spin mr-2" />
          Loading traces...
        </div>
      )}

      <ScrollArea className="flex-1">
        <div className="flex flex-col">
          {filteredTraces.map((trace) => {
            const displayStatus = getDisplayStatus(trace);
            const displayDuration =
              selectedDetail?.trace.trace_id === trace.trace_id
                ? selectedDetail.trace.duration_ms
                : trace.duration_ms;

            return (
              <button
                key={trace.trace_id}
                onClick={() => handleSelectTrace(trace.trace_id)}
                className={cn(
                  "flex flex-col gap-1.5 p-4 border-b border-border/50 hover:bg-muted/50 transition-colors text-left",
                  selectedTraceId === trace.trace_id &&
                    "bg-primary/5 border-l-2 border-l-primary",
                )}
              >
                <div className="flex items-center gap-2 w-full">
                  {getStatusDot(displayStatus)}
                  <span className="font-medium truncate flex-1 text-sm">
                    {trace.name}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground w-full">
                  <span className="font-mono text-[10px] opacity-60">
                    {trace.trace_id.slice(0, 8)}...
                  </span>
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span
                      className={cn(
                        displayStatus === "RUNNING" && "text-amber-500",
                      )}
                    >
                      {formatDuration(displayDuration)}
                    </span>
                  </div>
                </div>

                <div className="text-[11px] text-muted-foreground/70">
                  {formatDistanceToNow(new Date(trace.start_time), {
                    addSuffix: true,
                  })}
                </div>
              </button>
            );
          })}

          {filteredTraces.length === 0 && !isLoading && (
            <div className="p-8 text-center text-muted-foreground">
              <Activity className="h-8 w-8 mx-auto mb-2 opacity-20" />
              <p>No traces found</p>
              {searchTerm && (
                <p className="text-xs mt-1">Try adjusting your search</p>
              )}
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-3 border-t border-border bg-muted/20 text-xs text-muted-foreground">
        {filteredTraces.length} of {traces.length} traces
      </div>
    </div>
  );
}
