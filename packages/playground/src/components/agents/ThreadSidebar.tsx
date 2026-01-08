import { Link } from "react-router-dom";
import { Bot, Plus, ChevronRight, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useThreads, useCreateThread } from "@/hooks/use-threads";

interface ThreadSidebarProps {
  agentId: string;
  agentName?: string;
  selectedThreadId?: string | null;
  onThreadSelect: (threadId: string) => void;
  isCollapsed?: boolean;
  onToggle?: () => void;
}

export function ThreadSidebar({
  agentId,
  agentName,
  selectedThreadId,
  onThreadSelect,
  isCollapsed = false,
  onToggle,
}: ThreadSidebarProps) {
  const { data: threads, isLoading } = useThreads(agentId);
  const createThreadMutation = useCreateThread(agentId);

  const handleNewThread = () => {
    createThreadMutation.mutate(
      {
        title: undefined,
        message: undefined,
      },
      {
        onSuccess: (thread) => {
          onThreadSelect(thread.id);
        },
      }
    );
  };

  if (isCollapsed) {
    return (
      <aside className="hidden md:block w-0 overflow-hidden transition-all duration-300 border-r border-border">
        <div className="w-[220px]" />
      </aside>
    );
  }

  return (
    <aside className="hidden md:flex w-[220px] h-full flex-col border-r border-border transition-all duration-300">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1 border-b border-border px-4 py-3 text-sm">
        <Link
          to="/agents"
          className="text-muted-foreground hover:text-foreground"
        >
          <Bot className="h-4 w-4" />
        </Link>
        <ChevronRight className="h-3 w-3 text-muted-foreground" />
        <span className="text-foreground truncate flex-1">
          {agentName || "Agent"}
        </span>
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-1 text-muted-foreground hover:text-foreground transition-colors"
            title="Close sidebar"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* New Chat Button */}
      <div className="border-b border-border p-2">
        <button
          onClick={handleNewThread}
          disabled={createThreadMutation.isPending}
          className="flex w-full items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {isLoading && (
          <div className="flex items-center justify-center py-4">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        )}

        {threads?.map((thread) => (
          <button
            key={thread.id}
            onClick={() => onThreadSelect(thread.id)}
            className={cn(
              "w-full rounded-md px-3 py-2 text-left text-sm transition-colors",
              selectedThreadId === thread.id
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            )}
          >
            <p className="truncate font-medium">
              {thread.title || "Chat Session"}
            </p>
            <p className="text-xs text-muted-foreground">
              {new Date(thread.created_at).toLocaleDateString()}
            </p>
          </button>
        ))}

        {!isLoading && threads?.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <Bot className="h-8 w-8 mb-2 opacity-50" />
            <p className="text-xs">No conversations yet</p>
          </div>
        )}
      </div>
    </aside>
  );
}
