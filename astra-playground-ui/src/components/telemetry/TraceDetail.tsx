import { useState } from "react";
import { useAppSelector } from "@/store/hooks";
import {
  useGetTraceDetailQuery,
  useGetTraceLogsQuery,
} from "@/api/rtkApi";
import { skipToken } from "@reduxjs/toolkit/query/react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  Calendar,
  Hash,
  Activity,
  Layers,
  BarChart3,
  Copy,
  Check,
} from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import WaterfallTimeline from "./WaterfallTimeline";
import SpanTree from "./SpanTree";
import SpanDetailDrawer from "./SpanDetailDrawer";
import type { Span } from "@/types/api";
import type { LucideIcon } from "lucide-react";

type DetailTab = "timeline" | "spans";
interface DetailTabDef {
  id: DetailTab;
  label: string;
  icon: LucideIcon;
}

const TABS: DetailTabDef[] = [
  { id: "timeline", label: "Timeline", icon: BarChart3 },
  { id: "spans", label: "Span Tree", icon: Layers },
];

function formatDuration(ms: number | null): string {
  if (ms == null || ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

function isStringAttribute(value: unknown): value is string {
  return typeof value === "string";
}

function isNumberAttribute(value: unknown): value is number {
  return typeof value === "number";
}

export default function TraceDetail() {
  const selectedTraceId = useAppSelector(
    (state) => state.telemetry.selectedTraceId,
  );

  const { data: detail, isLoading: isLoadingDetail } = useGetTraceDetailQuery(
    selectedTraceId ?? skipToken,
  );
  const { data: logsResponse } = useGetTraceLogsQuery(
    selectedTraceId ? { traceId: selectedTraceId } : skipToken,
  );

  const selectedTrace = detail?.trace ?? null;
  const selectedTraceSpans = detail?.spans ?? [];
  const logs = logsResponse?.logs ?? [];

  const [activeTab, setActiveTab] = useState<DetailTab>("timeline");
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCopyTrace = () => {
    const traceData = {
      trace: selectedTrace,
      spans: selectedTraceSpans,
      logs,
    };
    void navigator.clipboard.writeText(JSON.stringify(traceData, null, 2));
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

  const traceStart = new Date(selectedTrace.start_time).getTime();
  const actualDuration = Math.max(
    selectedTrace.duration_ms ?? 0,
    ...selectedTraceSpans.map((s) => {
      const spanStart = new Date(s.start_time).getTime();
      return spanStart - traceStart + (s.duration_ms ?? 0);
    }),
    1,
  );
  const traceDuration = actualDuration;

  const totalTokens = selectedTraceSpans.reduce((sum, span) => {
    const t = span.attributes?.total_tokens;
    return sum + (isNumberAttribute(t) ? t : 0);
  }, 0);
  const toolCount = selectedTraceSpans.filter((s) => s.kind === "TOOL").length;

  const agentId = selectedTrace.attributes?.agent_id;
  const teamId = selectedTrace.attributes?.team_id;
  const threadId = selectedTrace.attributes?.thread_id;

  return (
    <div className="h-full flex overflow-hidden bg-background">
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-6 border-b border-border bg-card">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold mb-2">{selectedTrace.name}</h1>

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

              <div className="flex flex-wrap gap-2 mt-3">
                {isStringAttribute(agentId) && (
                  <Badge variant="secondary" className="text-xs">
                    agent: {agentId}
                  </Badge>
                )}
                {isStringAttribute(teamId) && (
                  <Badge variant="secondary" className="text-xs">
                    team: {teamId}
                  </Badge>
                )}
                {isStringAttribute(threadId) && (
                  <Badge variant="outline" className="text-xs font-mono">
                    thread: {threadId.slice(0, 8)}
                  </Badge>
                )}
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
                      {Math.round(selectedTrace.input_tokens).toLocaleString()}
                    </span>
                    <span className="opacity-40">|</span>
                    <span className="text-emerald-600 dark:text-emerald-400">
                      Out:{" "}
                      {Math.round(selectedTrace.output_tokens).toLocaleString()}
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
                  selectedSpanId={selectedSpan?.span_id ?? null}
                  logs={logs}
                />
              </div>
            </div>
          )}
        </ScrollArea>
      </div>

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
