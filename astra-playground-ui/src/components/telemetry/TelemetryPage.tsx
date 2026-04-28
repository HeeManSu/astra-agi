import { useState } from "react";
import TraceList from "./TraceList";
import TraceDetail from "./TraceDetail";
import { Activity, BarChart2 } from "lucide-react";
import { cn } from "@/lib/utils";

type TelemetryTab = "traces" | "metrics";

interface TabDef {
  id: TelemetryTab;
  label: string;
  icon: typeof Activity;
}

const TABS: TabDef[] = [
  { id: "traces", label: "Traces", icon: Activity },
  { id: "metrics", label: "Metrics", icon: BarChart2 },
];

export default function TelemetryPage() {
  const [activeTab, setActiveTab] = useState<TelemetryTab>("traces");

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background">
      <div className="flex border-b border-border bg-muted/20 px-4">
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

      {activeTab === "traces" && (
        <div className="flex-1 flex overflow-hidden">
          <div className="w-80 shrink-0 h-full">
            <TraceList />
          </div>
          <div className="flex-1 h-full overflow-hidden">
            <TraceDetail />
          </div>
        </div>
      )}

      {activeTab === "metrics" && (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <div className="text-center">
            <BarChart2 className="h-16 w-16 mx-auto mb-4 opacity-10" />
            <p className="text-lg font-medium">Metrics Dashboard</p>
            <p className="text-sm text-muted-foreground/60 mt-1">Coming soon</p>
          </div>
        </div>
      )}
    </div>
  );
}
