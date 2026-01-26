import { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "@/store/hooks";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  Calendar,
  Hash,
  Activity,
  Layers,
  BarChart3,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import WaterfallTimeline from "./WaterfallTimeline";
import SpanTree from "./SpanTree";
import SpanDetailDrawer from "./SpanDetailDrawer";

// Tabs for the detail view
const TABS = [
  { id: "timeline", label: "Timeline", icon: BarChart3 },
  { id: "spans", label: "Span Tree", icon: Layers },
];

export default function TraceDetail() {
  const dispatch = useAppDispatch();
  const { serverUrl, apiKey } = useAppSelector((state) => state.app);
  const { selectedTrace, selectedTraceSpans, isLoadingDetail } = useAppSelector(
    (state) => state.telemetry,
  );

  const [activeTab, setActiveTab] = useState("timeline");
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [logs, setLogs] = useState([]);
  const [copied, setCopied] = useState(false);

  // Fetch logs when trace changes
  useEffect(() => {
    if (selectedTrace?.trace_id && serverUrl) {
      fetchLogs();
    }
  }, [selectedTrace?.trace_id, serverUrl]);

  const fetchLogs = async () => {
    if (!serverUrl || !selectedTrace?.trace_id) return;

    try {
      const headers = { "Content-Type": "application/json" };
      if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;

      const baseUrl = serverUrl.replace(/\/$/, "");
      const response = await fetch(
        `${baseUrl}/observability/traces/${selectedTrace.trace_id}/logs`,
        { headers },
      );

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      }
    } catch (error) {
      console.error("Failed to fetch logs:", error);
    }
  };

  const handleCopyTrace = () => {
    const traceData = {
      trace: selectedTrace,
      spans: selectedTraceSpans,
      logs: logs,
    };
    navigator.clipboard.writeText(JSON.stringify(traceData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!selectedTrace) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-muted-foreground bg-muted/5">
        <Activity className="h-16 w-16 mb-4 opacity-10" />
        <p className="text-lg font-medium">Select a trace to view details</p>
        <p className="text-sm text-muted-foreground/60 mt-1">
          Choose a trace from the list on the left
        </p>
      </div>
    );
  }

  if (isLoadingDetail) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 animate-pulse" />
          Loading trace details...
        </div>
      </div>
    );
  }

  // Calculate trace metrics
  const traceStart = new Date(selectedTrace.start_time).getTime();

  // Calculate actual duration from spans if trace duration is not set
  const actualDuration = Math.max(
    selectedTrace.duration_ms || 0,
    ...selectedTraceSpans.map((s) => {
      const spanStart = new Date(s.start_time).getTime();
      return spanStart - traceStart + (s.duration_ms || 0);
    }),
    1, // minimum 1ms
  );

  const traceDuration = actualDuration;
  const totalTokens = selectedTraceSpans.reduce((sum, span) => {
    return sum + (span.attributes?.total_tokens || 0);
  }, 0);
  const toolCount = selectedTraceSpans.filter((s) => s.kind === "TOOL").length;

  // Format duration nicely
  const formatDuration = (ms) => {
    if (ms == null || ms < 1) return "<1ms";
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  };

  return (
    <div className="h-full flex overflow-hidden bg-background">
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-border bg-card">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold mb-2">{selectedTrace.name}</h1>

              {/* Quick Stats */}
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <Hash className="h-4 w-4" />
                  <span className="font-mono text-xs">
                    {selectedTrace.trace_id.slice(0, 12)}...
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-4 w-4" />
                  <span>
                    {format(
                      new Date(selectedTrace.start_time),
                      "MMM d, HH:mm:ss",
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="h-4 w-4" />
                  <span className="font-semibold text-foreground">
                    {formatDuration(traceDuration)}
                  </span>
                </div>
              </div>

              {/* Attribute Badges */}
              <div className="flex flex-wrap gap-2 mt-3">
                {selectedTrace.attributes?.agent_id && (
                  <Badge variant="secondary" className="text-xs">
                    agent: {selectedTrace.attributes.agent_id}
                  </Badge>
                )}
                {selectedTrace.attributes?.team_id && (
                  <Badge variant="secondary" className="text-xs">
                    team: {selectedTrace.attributes.team_id}
                  </Badge>
                )}
                {selectedTrace.attributes?.thread_id && (
                  <Badge variant="outline" className="text-xs font-mono">
                    thread: {selectedTrace.attributes.thread_id.slice(0, 8)}
                  </Badge>
                )}
                {/* Token metrics from trace model */}
                {(selectedTrace.total_tokens > 0 || totalTokens > 0) && (
                  <Badge
                    variant="outline"
                    className="text-xs bg-violet-50 dark:bg-violet-900/20 flex gap-2"
                  >
                    <span>
                      🔤{" "}
                      {Math.round(
                        selectedTrace.total_tokens || totalTokens,
                      ).toLocaleString()}{" "}
                      tokens
                    </span>
                    <span className="opacity-40">|</span>
                    <span className="text-blue-600 dark:text-blue-400">
                      In:{" "}
                      {Math.round(
                        selectedTrace.input_tokens || 0,
                      ).toLocaleString()}
                    </span>
                    <span className="opacity-40">|</span>
                    <span className="text-emerald-600 dark:text-emerald-400">
                      Out:{" "}
                      {Math.round(
                        selectedTrace.output_tokens || 0,
                      ).toLocaleString()}
                    </span>
                    {selectedTrace.thoughts_tokens > 0 && (
                      <>
                        <span className="opacity-40">|</span>
                        <span className="text-amber-600 dark:text-amber-400">
                          {Math.round(
                            selectedTrace.thoughts_tokens,
                          ).toLocaleString()}{" "}
                          thinking
                        </span>
                      </>
                    )}
                  </Badge>
                )}
                {selectedTrace.model && (
                  <Badge
                    variant="outline"
                    className="text-xs bg-blue-50 dark:bg-blue-900/20"
                  >
                    🤖 {selectedTrace.model}
                  </Badge>
                )}
                {selectedTraceSpans.length > 0 && (
                  <Badge variant="outline" className="text-xs">
                    {selectedTraceSpans.length} spans
                  </Badge>
                )}
                {toolCount > 0 && (
                  <Badge
                    variant="outline"
                    className="text-xs bg-orange-50 dark:bg-orange-900/20"
                  >
                    🔧 {toolCount} tools
                  </Badge>
                )}
              </div>
            </div>

            {/* Status and Actions */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyTrace}
                className="p-2 hover:bg-muted rounded-md transition-colors"
                title="Copy trace JSON"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
              <Badge
                variant={
                  selectedTrace.status === "ERROR" ? "destructive" : "default"
                }
                className={cn(
                  "text-sm px-3 py-1",
                  selectedTrace.status === "SUCCESS" &&
                    "bg-emerald-500 hover:bg-emerald-600",
                  selectedTrace.status === "RUNNING" &&
                    "bg-amber-500 hover:bg-amber-600",
                )}
              >
                {selectedTrace.status}
              </Badge>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-border bg-muted/30">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px",
                activeTab === tab.id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <ScrollArea className="flex-1 p-6">
          {activeTab === "timeline" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Execution Timeline
                </h3>
                <WaterfallTimeline
                  spans={selectedTraceSpans}
                  traceStart={selectedTrace.start_time}
                  traceDuration={traceDuration}
                  onSelectSpan={setSelectedSpan}
                />
              </div>
            </div>
          )}

          {activeTab === "spans" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  Span Hierarchy
                </h3>
                <SpanTree
                  spans={selectedTraceSpans}
                  onSelectSpan={setSelectedSpan}
                  selectedSpanId={selectedSpan?.span_id}
                  logs={logs}
                />
              </div>
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Span Detail Drawer */}
      {selectedSpan && (
        <SpanDetailDrawer
          span={selectedSpan}
          logs={logs}
          onClose={() => setSelectedSpan(null)}
        />
      )}
    </div>
  );
}
