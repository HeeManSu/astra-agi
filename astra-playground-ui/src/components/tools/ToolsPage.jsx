import { useState, useEffect, useCallback } from "react";
import { useAppSelector } from "@/store/hooks";
import { getTools, syncTools } from "@/api/tools";
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

const PAGE_SIZE = 15;

function ToolsPage() {
  const { serverUrl, apiKey, isConnected } = useAppSelector(
    (state) => state.app,
  );

  const [tools, setTools] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedTool, setSelectedTool] = useState(null);

  // Fetch tools
  const fetchTools = useCallback(async () => {
    if (!isConnected) return;

    setLoading(true);
    try {
      const response = await getTools(serverUrl, apiKey, {
        search,
        page,
        pageSize: PAGE_SIZE,
      });
      setTools(response.tools || []);
      setTotal(response.total || 0);
    } catch (error) {
      console.error("Failed to fetch tools:", error);
      toast.error("Failed to fetch tools");
    } finally {
      setLoading(false);
    }
  }, [serverUrl, apiKey, isConnected, search, page]);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  // Handle sync
  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncTools(serverUrl, apiKey);
      toast.success("Tools synced successfully");
      fetchTools();
    } catch (error) {
      console.error("Failed to sync tools:", error);
      toast.error("Failed to sync tools");
    } finally {
      setSyncing(false);
    }
  };

  // Handle search
  const handleSearch = (e) => {
    setSearch(e.target.value);
    setPage(1);
  };

  // Pagination
  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Source badge color
  const getSourceColor = (source) => {
    if (source?.startsWith("mcp:")) {
      return "text-purple-600";
    }
    if (source === "local") {
      return "text-blue-600";
    }
    return "text-gray-600";
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      {/* Header */}
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

      {/* Search */}
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

      {/* Table */}
      <div className="flex-1 overflow-hidden">
        {!isConnected ? (
          <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
            Connect to server to view tools
          </div>
        ) : loading ? (
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

      {/* Pagination */}
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

      {/* Tool Detail Dialog */}
      <ToolDetailDialog
        tool={selectedTool}
        open={!!selectedTool}
        onOpenChange={(open) => !open && setSelectedTool(null)}
        onSave={() => {
          fetchTools();
          setSelectedTool(null);
        }}
      />
    </div>
  );
}

export default ToolsPage;
