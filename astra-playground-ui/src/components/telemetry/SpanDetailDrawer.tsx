import { cn } from "@/lib/utils";
import {
  X,
  Clock,
  Hash,
  Tag,
  MessageSquare,
  AlertCircle,
  Info,
  Bug,
  AlertTriangle,
  Copy,
  Check,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { format } from "date-fns";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import type { Log, LogLevel, Span, SpanKind, SpanStatus } from "@/types/api";

interface LogLevelStyle {
  icon: LucideIcon;
  color: string;
  bg: string;
}

const LOG_LEVELS: Record<LogLevel, LogLevelStyle> = {
  DEBUG: { icon: Bug, color: "text-slate-500", bg: "bg-slate-500/10" },
  INFO: { icon: Info, color: "text-blue-500", bg: "bg-blue-500/10" },
  WARN: { icon: AlertTriangle, color: "text-amber-500", bg: "bg-amber-500/10" },
  WARNING: {
    icon: AlertTriangle,
    color: "text-amber-500",
    bg: "bg-amber-500/10",
  },
  ERROR: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-500/10" },
};

const STATUS_BADGE: Record<SpanStatus, string> = {
  SUCCESS:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  ERROR: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  RUNNING:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
};

const KIND_BADGE: Record<SpanKind, string> = {
  GENERATION:
    "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  TOOL: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  STEP: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  WORKFLOW: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
};

function formatDuration(ms: number | null): string {
  if (ms == null || ms === 0) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

interface SpanDetailDrawerProps {
  span: Span | null;
  logs: Log[];
  onClose: () => void;
  showDebug?: boolean;
}

export default function SpanDetailDrawer({
  span,
  logs,
  onClose,
  showDebug = false,
}: SpanDetailDrawerProps) {
  const [copiedId, setCopiedId] = useState(false);

  if (!span) return null;

  const spanLogs = logs.filter((log) => log.span_id === span.span_id);
  const filteredLogs = showDebug
    ? spanLogs
    : spanLogs.filter((log) => log.level !== "DEBUG");

  const handleCopySpanId = () => {
    void navigator.clipboard.writeText(span.span_id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  return (
    <div className="w-[400px] h-full border-l border-border bg-card flex flex-col shadow-xl">
      <div className="p-4 border-b border-border bg-muted/30">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg truncate">{span.name}</h3>
            <div className="flex items-center gap-2 mt-1.5">
              <span
                className={cn(
                  "text-xs font-medium px-2 py-0.5 rounded",
                  STATUS_BADGE[span.status] || "bg-muted",
                )}
              >
                {span.status}
              </span>
              {span.kind && (
                <span
                  className={cn(
                    "text-xs font-medium px-2 py-0.5 rounded",
                    KIND_BADGE[span.kind] || "bg-muted",
                  )}
                >
                  {span.kind}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-muted rounded-md transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
              Metrics
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2 p-2.5 bg-muted/50 rounded-lg">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="text-xs text-muted-foreground">Duration</div>
                  <div className="font-semibold">
                    {formatDuration(span.duration_ms)}
                  </div>
                </div>
              </div>
              <div
                className="flex items-center gap-2 p-2.5 bg-muted/50 rounded-lg cursor-pointer hover:bg-muted/70 transition-colors"
                onClick={handleCopySpanId}
                title="Click to copy full Span ID"
              >
                <Hash className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    Span ID
                    {copiedId ? (
                      <Check className="h-3 w-3 text-emerald-500" />
                    ) : (
                      <Copy className="h-3 w-3 opacity-50" />
                    )}
                  </div>
                  <div
                    className="font-mono text-xs truncate"
                    title={span.span_id}
                  >
                    {span.span_id}
                  </div>
                </div>
              </div>
            </div>

            <div className="text-xs text-muted-foreground space-y-1 bg-muted/30 p-2.5 rounded-lg">
              <div className="flex justify-between">
                <span>Start:</span>
                <span className="font-mono">
                  {span.start_time &&
                    format(new Date(span.start_time), "HH:mm:ss.SSS")}
                </span>
              </div>
              {span.end_time && (
                <div className="flex justify-between">
                  <span>End:</span>
                  <span className="font-mono">
                    {format(new Date(span.end_time), "HH:mm:ss.SSS")}
                  </span>
                </div>
              )}
            </div>
          </div>

          {span.attributes && Object.keys(span.attributes).length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-2">
                <Tag className="h-4 w-4" />
                Attributes
              </h4>
              <div className="space-y-2">
                {Object.entries(span.attributes).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex flex-col p-2.5 bg-muted/30 rounded-lg"
                  >
                    <span className="text-[10px] font-medium text-muted-foreground uppercase">
                      {key}
                    </span>
                    <span className="text-sm font-mono break-all mt-0.5">
                      {typeof value === "object"
                        ? JSON.stringify(value, null, 2)
                        : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {span.error && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-red-500 flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Error
              </h4>
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-700 dark:text-red-300 font-mono">
                {span.error}
              </div>
            </div>
          )}

          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Logs ({filteredLogs.length})
            </h4>

            {filteredLogs.length === 0 ? (
              <div className="text-sm text-muted-foreground p-4 text-center bg-muted/30 rounded-lg">
                No logs for this span
              </div>
            ) : (
              <div className="space-y-1.5">
                {filteredLogs.map((log, idx) => {
                  const levelConfig = LOG_LEVELS[log.level] ?? LOG_LEVELS.INFO;
                  const Icon = levelConfig.icon;

                  return (
                    <div
                      key={log.id || idx}
                      className={cn(
                        "flex items-start gap-2 p-2.5 rounded-lg text-sm",
                        levelConfig.bg,
                      )}
                    >
                      <Icon
                        className={cn(
                          "h-4 w-4 mt-0.5 shrink-0",
                          levelConfig.color,
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "text-[10px] font-semibold uppercase",
                              levelConfig.color,
                            )}
                          >
                            {log.level}
                          </span>
                          <span className="text-[10px] text-muted-foreground font-mono">
                            {log.timestamp &&
                              format(new Date(log.timestamp), "HH:mm:ss.SSS")}
                          </span>
                        </div>
                        <p className="text-foreground mt-0.5 break-words">
                          {log.message}
                        </p>

                        {log.attributes &&
                          Object.keys(log.attributes).length > 0 && (
                            <div className="mt-1.5 text-xs text-muted-foreground font-mono">
                              {Object.entries(log.attributes).map(([k, v]) => (
                                <div key={k} className="truncate">
                                  {k}:{" "}
                                  {typeof v === "object"
                                    ? JSON.stringify(v)
                                    : String(v)}
                                </div>
                              ))}
                            </div>
                          )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
