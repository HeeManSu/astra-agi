import { useState } from "react";
import { cn } from "@/lib/utils";
import { ChevronRight, ChevronDown, Clock, MessageSquare } from "lucide-react";
import type { Log, Span, SpanKind, SpanStatus } from "@/types/api";

const STATUS_DOT_COLORS: Record<SpanStatus, string> = {
  SUCCESS: "bg-emerald-500",
  ERROR: "bg-red-500",
  RUNNING: "bg-amber-500 animate-pulse",
};

const KIND_BADGES: Record<SpanKind, string> = {
  GENERATION:
    "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
  TOOL: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  STEP: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  WORKFLOW: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300",
};

interface SpanNodeData extends Span {
  children: SpanNodeData[];
}

function buildSpanTree(spans: Span[]): SpanNodeData[] {
  const spanMap = new Map<string, SpanNodeData>();
  const roots: SpanNodeData[] = [];

  spans.forEach((span) => {
    spanMap.set(span.span_id, { ...span, children: [] });
  });

  spans.forEach((span) => {
    const node = spanMap.get(span.span_id);
    if (!node) return;
    if (span.parent_span_id && spanMap.has(span.parent_span_id)) {
      spanMap.get(span.parent_span_id)?.children.push(node);
    } else {
      roots.push(node);
    }
  });

  return roots;
}

interface SpanNodeProps {
  span: SpanNodeData;
  depth?: number;
  onSelectSpan?: ((span: Span) => void) | undefined;
  selectedSpanId?: string | null | undefined;
  logs?: Log[] | undefined;
}

function SpanNode({
  span,
  depth = 0,
  onSelectSpan,
  selectedSpanId,
  logs,
}: SpanNodeProps) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = span.children.length > 0;

  const logCount = logs?.filter((log) => log.span_id === span.span_id).length ?? 0;

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(!expanded);
  };

  const handleClick = () => {
    onSelectSpan?.(span);
  };

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-2 py-2 px-2 rounded-md cursor-pointer transition-colors",
          "hover:bg-muted/50",
          selectedSpanId === span.span_id &&
            "bg-primary/10 border-l-2 border-l-primary",
        )}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        onClick={handleClick}
      >
        <button
          onClick={handleToggle}
          className={cn(
            "p-0.5 rounded hover:bg-muted transition-colors",
            !hasChildren && "invisible",
          )}
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </button>

        <span
          className={cn(
            "w-2 h-2 rounded-full",
            STATUS_DOT_COLORS[span.status] || "bg-gray-400",
          )}
        />

        <span className="font-medium text-sm flex-1 truncate">{span.name}</span>

        {span.kind && (
          <span
            className={cn(
              "text-[10px] font-medium px-1.5 py-0.5 rounded",
              KIND_BADGES[span.kind] || "bg-muted text-muted-foreground",
            )}
          >
            {span.kind}
          </span>
        )}

        {logCount > 0 && (
          <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground">
            <MessageSquare className="h-3 w-3" />
            {logCount}
          </span>
        )}

        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {span.duration_ms ?? 0}ms
        </span>
      </div>

      {expanded && hasChildren && (
        <div>
          {span.children.map((child) => (
            <SpanNode
              key={child.span_id}
              span={child}
              depth={depth + 1}
              onSelectSpan={onSelectSpan}
              selectedSpanId={selectedSpanId}
              logs={logs}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface SpanTreeProps {
  spans: Span[];
  onSelectSpan?: (span: Span) => void;
  selectedSpanId?: string | null;
  logs?: Log[];
}

export default function SpanTree({
  spans,
  onSelectSpan,
  selectedSpanId,
  logs,
}: SpanTreeProps) {
  const tree = buildSpanTree(spans ?? []);

  if (tree.length === 0) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        No spans to display
      </div>
    );
  }

  return (
    <div className="py-2">
      {tree.map((span) => (
        <SpanNode
          key={span.span_id}
          span={span}
          onSelectSpan={onSelectSpan}
          selectedSpanId={selectedSpanId}
          logs={logs}
        />
      ))}
    </div>
  );
}
