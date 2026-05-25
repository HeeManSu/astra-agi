import { useState } from "react";
import { useGetMetricsQuery } from "@/api/rtkApi";
import { cn } from "@/lib/utils";
import {
  Activity,
  AlertCircle,
  BarChart2,
  Clock,
  Cpu,
  Hash,
  RefreshCw,
  Sparkles,
  Users,
  Wrench,
  Zap,
} from "lucide-react";
import type { MetricsResponse, TopItem } from "@/types/api";

const WINDOWS: { label: string; hours: number }[] = [
  { label: "1h", hours: 1 },
  { label: "24h", hours: 24 },
  { label: "7d", hours: 24 * 7 },
  { label: "30d", hours: 24 * 30 },
];

function formatDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1) return "<1ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 60_000).toFixed(2)}m`;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toLocaleString();
}

function formatPct(frac: number): string {
  return `${(frac * 100).toFixed(1)}%`;
}

export default function MetricsDashboard() {
  const [hours, setHours] = useState<number>(24);
  const { data, isLoading, isFetching, refetch } = useGetMetricsQuery({
    hours,
  });

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background">
      <div className="flex items-center justify-between p-4 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          <BarChart2 className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Metrics</h2>
          {data && (
            <span className="text-xs text-muted-foreground ml-2">
              {data.trace_sample_size} traces
              {data.truncated && " (capped)"}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-border overflow-hidden">
            {WINDOWS.map((w) => (
              <button
                key={w.hours}
                onClick={() => setHours(w.hours)}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium transition-colors",
                  hours === w.hours
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted",
                )}
              >
                {w.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => refetch()}
            className="p-2 rounded-md hover:bg-muted transition-colors"
            title="Refresh"
          >
            <RefreshCw
              className={cn("h-4 w-4", isFetching && "animate-spin")}
            />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {isLoading && !data && (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <Activity className="h-5 w-5 animate-pulse mr-2" />
            Loading metrics...
          </div>
        )}

        {data && data.request_count === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
            <BarChart2 className="h-12 w-12 opacity-20 mb-3" />
            <p>No traces in the selected window</p>
            <p className="text-sm text-muted-foreground/60 mt-1">
              Run an agent or team to populate metrics
            </p>
          </div>
        )}

        {data && data.request_count > 0 && <DashboardBody data={data} />}
      </div>
    </div>
  );
}

function DashboardBody({ data }: { data: MetricsResponse }) {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Kpi
          icon={Hash}
          label="Requests"
          value={formatNumber(data.request_count)}
          sub={`${data.success_count} ok · ${data.error_count} err${
            data.running_count > 0 ? ` · ${data.running_count} running` : ""
          }`}
        />
        <Kpi
          icon={data.error_rate > 0 ? AlertCircle : Activity}
          label="Success rate"
          value={formatPct(data.success_rate)}
          sub={`${formatPct(data.error_rate)} errors`}
          accent={
            data.error_rate > 0.1
              ? "red"
              : data.error_rate > 0
                ? "amber"
                : "emerald"
          }
        />
        <Kpi
          icon={Clock}
          label="Latency p50 / p95"
          value={formatDuration(data.latency_p50_ms)}
          sub={`p95 ${formatDuration(data.latency_p95_ms)}`}
        />
        <Kpi
          icon={Sparkles}
          label="Total tokens"
          value={formatNumber(data.total_tokens)}
          sub={`${formatNumber(Math.round(data.avg_tokens_per_request))} avg/req`}
        />
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Kpi
          icon={Zap}
          label="Avg TTFT"
          value={formatDuration(data.avg_ttft_ms)}
          sub="Time-to-first-token (gen)"
        />
        <Kpi
          icon={Cpu}
          label="Gen latency p50 / p95"
          value={formatDuration(data.generation_p50_ms)}
          sub={`p95 ${formatDuration(data.generation_p95_ms)}`}
        />
        <Kpi
          icon={Wrench}
          label="Tool calls"
          value={formatNumber(data.tool_call_count)}
          sub={`${data.tool_error_count} errors (${formatPct(data.tool_error_rate)})`}
          accent={
            data.tool_error_rate > 0.1
              ? "red"
              : data.tool_error_rate > 0
                ? "amber"
                : undefined
          }
        />
        <Kpi
          icon={Sparkles}
          label="In / Out tokens"
          value={`${formatNumber(data.input_tokens)} / ${formatNumber(data.output_tokens)}`}
          sub={
            data.thoughts_tokens > 0
              ? `${formatNumber(data.thoughts_tokens)} thinking`
              : "in / out"
          }
        />
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <TopList
          icon={Cpu}
          title="Top models"
          items={data.top_models}
          extraColumn={(item) => {
            const t = item.extra?.total_tokens;
            return typeof t === "number"
              ? `${formatNumber(t)} tokens`
              : null;
          }}
        />
        <TopList
          icon={Wrench}
          title="Top tools"
          items={data.top_tools}
          extraColumn={(item) => {
            const errs =
              typeof item.extra?.error_count === "number"
                ? item.extra.error_count
                : 0;
            const rate =
              typeof item.extra?.error_rate === "number"
                ? item.extra.error_rate
                : 0;
            if (errs === 0) return "no errors";
            return (
              <span className="text-red-600 dark:text-red-400">
                {errs} err ({formatPct(rate)})
              </span>
            );
          }}
        />
        <TopList icon={Users} title="Top agents" items={data.top_agents} />
        <TopList icon={Users} title="Top teams" items={data.top_teams} />
      </section>
    </div>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  sub?: string;
  accent?: "emerald" | "red" | "amber" | undefined;
}) {
  const accentClass =
    accent === "emerald"
      ? "text-emerald-600 dark:text-emerald-400"
      : accent === "red"
        ? "text-red-600 dark:text-red-400"
        : accent === "amber"
          ? "text-amber-600 dark:text-amber-400"
          : "text-foreground";
  return (
    <div className="p-4 rounded-lg border border-border bg-card">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className={cn("mt-2 text-2xl font-bold tabular-nums", accentClass)}>
        {value}
      </div>
      {sub && (
        <div className="mt-1 text-xs text-muted-foreground tabular-nums">
          {sub}
        </div>
      )}
    </div>
  );
}

function TopList({
  icon: Icon,
  title,
  items,
  extraColumn,
}: {
  icon: typeof Activity;
  title: string;
  items: TopItem[];
  extraColumn?: (item: TopItem) => React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2 text-sm font-semibold">
        <Icon className="h-4 w-4" />
        {title}
      </div>
      {items.length === 0 ? (
        <div className="px-4 py-6 text-sm text-muted-foreground text-center">
          No data
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <li
              key={item.name}
              className="px-4 py-2.5 flex items-center justify-between text-sm"
            >
              <span className="font-mono truncate mr-3">{item.name}</span>
              <div className="flex items-center gap-3 shrink-0 text-xs">
                {extraColumn && (
                  <span className="text-muted-foreground tabular-nums">
                    {extraColumn(item)}
                  </span>
                )}
                <span className="px-2 py-0.5 rounded bg-muted font-semibold tabular-nums">
                  {item.count}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
