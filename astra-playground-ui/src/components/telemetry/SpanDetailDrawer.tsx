import { cn, parseTimestamp } from "@/lib/utils";
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
                    format(parseTimestamp(span.start_time), "HH:mm:ss.SSS")}
                </span>
              </div>
              {span.end_time && (
                <div className="flex justify-between">
                  <span>End:</span>
                  <span className="font-mono">
                    {format(parseTimestamp(span.end_time), "HH:mm:ss.SSS")}
                  </span>
                </div>
              )}
            </div>
          </div>

          {span.kind === "GENERATION" && (
            <GenerationSummary attributes={span.attributes ?? {}} />
          )}

          {span.kind === "TOOL" && (
            <ToolSummary attributes={span.attributes ?? {}} />
          )}

          {span.attributes && Object.keys(span.attributes).length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-2">
                <Tag className="h-4 w-4" />
                Attributes
                {!showDebug &&
                  Object.keys(span.attributes).some((k) => k.endsWith("_full")) && (
                    <span className="text-[10px] normal-case font-normal text-amber-600 dark:text-amber-400">
                      (turn on Debug to see *_full payloads)
                    </span>
                  )}
              </h4>
              <div className="space-y-2">
                {Object.entries(span.attributes)
                  .filter(([key]) => showDebug || !key.endsWith("_full"))
                  .map(([key, value]) => (
                    <div
                      key={key}
                      className={cn(
                        "flex flex-col p-2.5 rounded-lg",
                        key.endsWith("_full")
                          ? "bg-amber-500/5 border border-amber-500/20"
                          : "bg-muted/30",
                      )}
                    >
                      <span className="text-[10px] font-medium text-muted-foreground uppercase">
                        {key}
                      </span>
                      <span className="text-sm font-mono break-all mt-0.5 whitespace-pre-wrap">
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
                              format(parseTimestamp(log.timestamp), "HH:mm:ss.SSS")}
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

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function GenerationSummary({
  attributes,
}: {
  attributes: Record<string, unknown>;
}) {
  const model = asString(attributes.model);
  const provider = asString(attributes.provider);
  const ttft = asNumber(attributes.ttft_ms);
  const totalDuration = asNumber(attributes.total_duration_ms);
  const latency = asNumber(attributes.latency_ms);
  const inputTokens = asNumber(attributes.input_tokens);
  const outputTokens = asNumber(attributes.output_tokens);
  const thoughtsTokens = asNumber(attributes.thoughts_tokens);
  const totalTokens = asNumber(attributes.total_tokens);
  const chunkCount = asNumber(attributes.chunk_count);
  const contentChunks = asNumber(attributes.content_chunks);
  const toolCallChunks = asNumber(attributes.tool_call_chunks);

  const hasAnything =
    model ||
    ttft != null ||
    totalDuration != null ||
    latency != null ||
    totalTokens != null ||
    chunkCount != null;
  if (!hasAnything) return null;

  return (
    <div className="space-y-2 p-3 rounded-lg border border-violet-500/20 bg-violet-500/5">
      <h4 className="text-[11px] font-semibold uppercase tracking-wide text-violet-700 dark:text-violet-300">
        Generation
      </h4>
      <div className="grid grid-cols-2 gap-2 text-xs">
        {model && (
          <Pill label="Model" value={provider ? `${provider} / ${model}` : model} mono />
        )}
        {ttft != null && <Pill label="TTFT" value={`${ttft.toFixed(0)} ms`} />}
        {latency != null && (
          <Pill label="Latency" value={`${latency.toFixed(0)} ms`} />
        )}
        {totalDuration != null && (
          <Pill label="Total" value={`${totalDuration.toFixed(0)} ms`} />
        )}
        {inputTokens != null && (
          <Pill label="Input tokens" value={inputTokens.toLocaleString()} accent="blue" />
        )}
        {outputTokens != null && (
          <Pill label="Output tokens" value={outputTokens.toLocaleString()} accent="emerald" />
        )}
        {thoughtsTokens != null && thoughtsTokens > 0 && (
          <Pill label="Thinking" value={thoughtsTokens.toLocaleString()} accent="amber" />
        )}
        {totalTokens != null && (
          <Pill label="Total tokens" value={totalTokens.toLocaleString()} accent="violet" />
        )}
        {chunkCount != null && (
          <Pill
            label="Chunks"
            value={
              contentChunks != null || toolCallChunks != null
                ? `${chunkCount} (${contentChunks ?? 0}c / ${toolCallChunks ?? 0}t)`
                : String(chunkCount)
            }
          />
        )}
      </div>
    </div>
  );
}

function ToolSummary({
  attributes,
}: {
  attributes: Record<string, unknown>;
}) {
  const toolName = asString(attributes.tool_name);
  const qualified = asString(attributes.tool_qualified_name);
  const isAsync = attributes.is_async;
  const resultType = asString(attributes.result_type);
  const argsPreview = attributes.args_preview;
  const resultPreview = attributes.result_preview;

  if (!toolName && !qualified && argsPreview == null && resultPreview == null) {
    return null;
  }

  return (
    <div className="space-y-2 p-3 rounded-lg border border-orange-500/20 bg-orange-500/5">
      <h4 className="text-[11px] font-semibold uppercase tracking-wide text-orange-700 dark:text-orange-300">
        Tool Call
      </h4>
      <div className="grid grid-cols-2 gap-2 text-xs">
        {toolName && <Pill label="Tool" value={toolName} mono />}
        {qualified && qualified !== toolName && (
          <Pill label="Qualified" value={qualified} mono />
        )}
        {typeof isAsync === "boolean" && (
          <Pill label="Async" value={isAsync ? "yes" : "no"} />
        )}
        {resultType && <Pill label="Result type" value={resultType} mono />}
      </div>
      {argsPreview != null && (
        <div className="text-xs">
          <div className="text-[10px] font-medium text-muted-foreground uppercase mb-1">
            Args
          </div>
          <pre className="font-mono text-[11px] whitespace-pre-wrap break-all bg-background/60 p-2 rounded">
            {typeof argsPreview === "object"
              ? JSON.stringify(argsPreview, null, 2)
              : String(argsPreview)}
          </pre>
        </div>
      )}
      {resultPreview != null && (
        <div className="text-xs">
          <div className="text-[10px] font-medium text-muted-foreground uppercase mb-1">
            Result
          </div>
          <pre className="font-mono text-[11px] whitespace-pre-wrap break-all bg-background/60 p-2 rounded">
            {typeof resultPreview === "object"
              ? JSON.stringify(resultPreview, null, 2)
              : String(resultPreview)}
          </pre>
        </div>
      )}
    </div>
  );
}

function Pill({
  label,
  value,
  mono,
  accent,
}: {
  label: string;
  value: string;
  mono?: boolean;
  accent?: "blue" | "emerald" | "amber" | "violet";
}) {
  const accentClass =
    accent === "blue"
      ? "text-blue-600 dark:text-blue-400"
      : accent === "emerald"
        ? "text-emerald-600 dark:text-emerald-400"
        : accent === "amber"
          ? "text-amber-600 dark:text-amber-400"
          : accent === "violet"
            ? "text-violet-600 dark:text-violet-400"
            : "text-foreground";
  return (
    <div className="flex flex-col p-2 rounded bg-background/60">
      <span className="text-[10px] font-medium text-muted-foreground uppercase">
        {label}
      </span>
      <span
        className={cn(
          "mt-0.5 font-semibold break-all",
          mono && "font-mono text-[11px]",
          accentClass,
        )}
      >
        {value}
      </span>
    </div>
  );
}
