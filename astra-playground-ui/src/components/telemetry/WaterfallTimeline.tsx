import { cn } from "@/lib/utils";
import type { Span, SpanKind, SpanStatus } from "@/types/api";

interface KindStyle {
  bg: string;
  border: string;
  text: string;
}

const KIND_COLORS: Record<SpanKind | "DEFAULT", KindStyle> = {
  GENERATION: {
    bg: "bg-violet-500/30",
    border: "border-violet-500/50",
    text: "text-violet-700 dark:text-violet-300",
  },
  TOOL: {
    bg: "bg-orange-500/30",
    border: "border-orange-500/50",
    text: "text-orange-700 dark:text-orange-300",
  },
  STEP: {
    bg: "bg-blue-500/30",
    border: "border-blue-500/50",
    text: "text-blue-700 dark:text-blue-300",
  },
  WORKFLOW: {
    bg: "bg-cyan-500/30",
    border: "border-cyan-500/50",
    text: "text-cyan-700 dark:text-cyan-300",
  },
  DEFAULT: {
    bg: "bg-slate-500/30",
    border: "border-slate-500/50",
    text: "text-slate-700 dark:text-slate-300",
  },
};

const STATUS_COLORS: Record<SpanStatus, string> = {
  SUCCESS: "border-l-emerald-500",
  ERROR: "border-l-red-500",
  RUNNING: "border-l-amber-500",
};

interface WaterfallTimelineProps {
  spans: Span[];
  traceStart: string;
  traceDuration: number | null;
  onSelectSpan?: (span: Span) => void;
}

function formatDuration(ms: number): string {
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60000).toFixed(2)}m`;
}

export default function WaterfallTimeline({
  spans,
  traceStart,
  traceDuration,
  onSelectSpan,
}: WaterfallTimelineProps) {
  if (!spans || spans.length === 0) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        No spans to display
      </div>
    );
  }

  const traceStartMs = new Date(traceStart).getTime();

  const actualMaxDuration = Math.max(
    traceDuration ?? 1,
    ...spans.map((s) => {
      const spanStart = new Date(s.start_time).getTime();
      return spanStart - traceStartMs + (s.duration_ms ?? 0);
    }),
  );

  const timeScale = actualMaxDuration;
  const markers = [0, 0.25, 0.5, 0.75, 1].map((pct) => ({
    pct,
    label: formatDuration(timeScale * pct),
  }));

  return (
    <div className="space-y-1">
      <div className="flex items-center text-[10px] text-muted-foreground mb-3 px-2">
        <div className="w-40 pr-4 text-right font-medium shrink-0">
          Operation
        </div>
        <div className="flex-1 relative h-4 flex justify-between">
          {markers.map((marker, idx) => (
            <span key={idx} className="text-center" style={{ width: "20%" }}>
              {marker.label}
            </span>
          ))}
        </div>
      </div>

      {spans.map((span) => {
        const spanStart = new Date(span.start_time).getTime();
        const offsetMs = Math.max(0, spanStart - traceStartMs);
        const durationMs = span.duration_ms ?? 1;

        const leftPercent = (offsetMs / timeScale) * 100;
        const widthPercent = Math.max(3, (durationMs / timeScale) * 100);

        const kindColors = KIND_COLORS[span.kind] ?? KIND_COLORS.DEFAULT;
        const statusBorder = STATUS_COLORS[span.status] ?? "";

        return (
          <div
            key={span.span_id}
            className="group relative flex items-center h-10 hover:bg-muted/30 rounded cursor-pointer transition-colors"
            onClick={() => onSelectSpan?.(span)}
          >
            <div className="w-40 pr-4 truncate text-xs text-right font-medium text-muted-foreground group-hover:text-foreground transition-colors shrink-0">
              {span.name}
            </div>

            <div className="flex-1 h-full relative bg-muted/20 rounded">
              {[0.25, 0.5, 0.75].map((pct) => (
                <div
                  key={pct}
                  className="absolute top-0 bottom-0 border-l border-border/30"
                  style={{ left: `${pct * 100}%` }}
                />
              ))}

              <div
                className={cn(
                  "absolute top-1.5 h-7 rounded flex items-center px-2 text-[11px] font-semibold overflow-hidden",
                  "border border-l-2 shadow-sm",
                  kindColors.bg,
                  kindColors.border,
                  kindColors.text,
                  statusBorder,
                )}
                style={{
                  left: `${leftPercent}%`,
                  width: `${widthPercent}%`,
                  minWidth: "40px",
                }}
              >
                <span className="truncate">{formatDuration(durationMs)}</span>
              </div>

              <div
                className="opacity-0 group-hover:opacity-100 transition-opacity absolute z-30 bg-popover text-popover-foreground text-xs px-3 py-2 rounded-lg shadow-lg border whitespace-nowrap pointer-events-none"
                style={{
                  left: `${Math.min(leftPercent, 70)}%`,
                  top: "-45px",
                }}
              >
                <div className="font-semibold mb-1">{span.name}</div>
                <div className="text-muted-foreground space-x-2">
                  <span>{formatDuration(durationMs)}</span>
                  <span>•</span>
                  <span>{span.kind || "STEP"}</span>
                  <span>•</span>
                  <span
                    className={
                      span.status === "ERROR"
                        ? "text-red-500"
                        : "text-emerald-500"
                    }
                  >
                    {span.status}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      })}

      <div className="flex items-center justify-end text-xs text-muted-foreground pt-2 pr-2 border-t border-border/50 mt-2">
        Total:{" "}
        <span className="font-semibold ml-1">
          {formatDuration(actualMaxDuration)}
        </span>
      </div>
    </div>
  );
}
