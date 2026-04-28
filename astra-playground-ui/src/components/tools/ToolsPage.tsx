import { useState } from "react";
import { useAppSelector } from "@/store/hooks";
import { useGetToolsQuery, useSyncToolsMutation } from "@/api/rtkApi";
import { skipToken } from "@reduxjs/toolkit/query/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Wrench,
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import ToolDetailDialog from "./ToolDetailDialog";
import type { Tool } from "@/types/api";

const PAGE_SIZE = 15;

function getSourceColor(source: string): string {
  if (source.startsWith("mcp:")) return "text-purple-600";
  if (source === "local") return "text-blue-600";
  return "text-gray-600";
}

function ToolsPage() {
  const isConnected = useAppSelector((state) => state.app.isConnected);

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);

  const { data, isFetching } = useGetToolsQuery(
    isConnected ? { search, page, pageSize: PAGE_SIZE } : skipToken,
  );
  const tools = data?.tools ?? [];
  const total = data?.total ?? 0;

  const [triggerSync, { isLoading: syncing }] = useSyncToolsMutation();

  const handleSync = async () => {
    try {
      await triggerSync().unwrap();
      toast.success("Tools synced successfully");
    } catch (error) {
      console.error("Failed to sync tools:", error);
      toast.error("Failed to sync tools");
    }
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      <div className="px-6 py-5 border-b">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-lg font-semibold flex items-center gap-2">
              <Wrench className="h-4 w-4" />
              Tool Definitions
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Semantic layer for AI agents. View and edit tool schemas.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={syncing || !isConnected}
            className="h-8"
          >
            <RefreshCw
              className={cn("h-3.5 w-3.5 mr-1.5", syncing && "animate-spin")}
            />
            {syncing ? "Syncing..." : "Sync Tools"}
          </Button>
        </div>
      </div>

      <div className="px-6 py-3">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search tools..."
            value={search}
            onChange={handleSearch}
            className="pl-9 h-9 text-sm"
          />
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {!isConnected ? (
          <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
            Connect to server to view tools
          </div>
        ) : isFetching && tools.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : tools.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <Wrench className="h-10 w-10 mb-3 opacity-50" />
            <p className="font-medium">No tools found</p>
            <p className="text-sm">
              {search
                ? "Try a different search"
                : "Tools will appear here after sync"}
            </p>
          </div>
        ) : (
          <ScrollArea className="h-full">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-background border-b">
                <tr className="text-left text-muted-foreground">
                  <th className="pl-6 pr-2 py-2.5 font-medium w-8">
                    <Wrench className="h-3.5 w-3.5" />
                  </th>
                  <th className="px-3 py-2.5 font-medium">Name</th>
                  <th className="px-3 py-2.5 font-medium">Source</th>
                  <th className="px-3 py-2.5 font-medium">Description</th>
                  <th className="px-3 py-2.5 font-medium">Version</th>
                  <th className="px-3 pr-6 py-2.5 font-medium text-right">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tools.map((tool) => (
                  <tr
                    key={tool.slug}
                    className="hover:bg-muted/40 cursor-pointer transition-colors"
                    onClick={() => setSelectedTool(tool)}
                  >
                    <td className="pl-6 pr-2 py-2.5">
                      <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
                    </td>
                    <td className="px-3 py-2.5 font-medium">{tool.name}</td>
                    <td className="px-3 py-2.5">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          getSourceColor(tool.source),
                        )}
                      >
                        {tool.source}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground max-w-md truncate">
                      {tool.description || "-"}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">
                      {tool.version || "1.0.0"}
                    </td>
                    <td className="px-3 pr-6 py-2.5 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedTool(tool);
                        }}
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollArea>
        )}
      </div>

      {total > 0 && (
        <div className="border-t px-6 py-3 flex items-center justify-between text-sm">
          <div className="text-muted-foreground">
            Showing 1 to {Math.min(tools.length, PAGE_SIZE)} of {total} tools
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </Button>
            <span className="px-2 text-muted-foreground">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      <ToolDetailDialog
        tool={selectedTool}
        open={selectedTool !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedTool(null);
        }}
        onSave={() => setSelectedTool(null)}
      />
    </div>
  );
}

export default ToolsPage;
