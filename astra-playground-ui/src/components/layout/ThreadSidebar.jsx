import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  fetchThreads,
  createNewThread,
  setCurrentThread,
  fetchThreadMessages,
  selectThreads,
  selectCurrentThreadId,
  selectIsLoading,
} from "@/store/slices/threadSlice";
import {
  clearSession,
  setMessages,
  setCurrentSession,
} from "@/store/slices/chatSlice";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Plus, MessageSquare, Loader2, Bot, Users } from "lucide-react";
import { cn } from "@/lib/utils";

function ThreadSidebar() {
  const dispatch = useAppDispatch();
  const { serverUrl, apiKey, selectedItem, isConnected } = useAppSelector(
    (state) => state.app
  );
  const threads = useAppSelector(selectThreads);
  const currentThreadId = useAppSelector(selectCurrentThreadId);
  const isLoading = useAppSelector(selectIsLoading);

  // Fetch threads when agent/team is selected
  useEffect(() => {
    if (isConnected && selectedItem && serverUrl) {
      dispatch(
        fetchThreads({
          serverUrl,
          apiKey,
          resourceType: selectedItem.type,
          resourceId: selectedItem.id,
        })
      );
    }
  }, [dispatch, isConnected, selectedItem, serverUrl, apiKey]);

  const handleNewChat = async () => {
    if (!selectedItem) return;

    const result = await dispatch(
      createNewThread({
        serverUrl,
        apiKey,
        data: {
          resource_type: selectedItem.type,
          resource_id: selectedItem.id,
          resource_name: selectedItem.data?.name || selectedItem.id,
          title: "New Chat",
        },
      })
    );

    if (createNewThread.fulfilled.match(result)) {
      const newThread = result.payload;
      // Set session to use thread ID
      const sessionKey = `thread:${newThread.id}`;
      dispatch(setCurrentSession(sessionKey));
      dispatch(clearSession(sessionKey));
    }
  };

  const handleSelectThread = async (threadId) => {
    dispatch(setCurrentThread(threadId));

    // Set session key based on thread
    const sessionKey = `thread:${threadId}`;
    dispatch(setCurrentSession(sessionKey));

    // Load messages for this thread
    const result = await dispatch(
      fetchThreadMessages({
        serverUrl,
        apiKey,
        threadId,
      })
    );

    if (fetchThreadMessages.fulfilled.match(result)) {
      dispatch(
        setMessages({
          sessionKey,
          messages: result.payload,
        })
      );
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  // Don't show if no item selected
  if (!selectedItem) {
    return null;
  }

  const itemName = selectedItem.data?.name || selectedItem.id;
  const ItemIcon = selectedItem.type === "agent" ? Bot : Users;

  return (
    <div className="w-64 h-full bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Agent/Team Header - h-14 to match ChatArea header */}
      <div className="h-14 px-4 border-b border-sidebar-border flex items-center">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-md bg-primary/10 flex items-center justify-center">
            <ItemIcon className="h-4 w-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">{itemName}</p>
            <p className="text-xs text-muted-foreground capitalize">
              {selectedItem.type}
            </p>
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-3 border-b border-sidebar-border">
        <Button
          onClick={handleNewChat}
          variant="ghost"
          className="w-full justify-start gap-2 text-primary hover:text-primary hover:bg-primary/10"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Threads List */}
      <ScrollArea className="flex-1">
        <div className="py-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : threads.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-8">
              No conversations yet
            </p>
          ) : (
            threads.map((thread, index) => (
              <div key={thread.id}>
                {/* Full-width divider between items */}
                {index > 0 && (
                  <div className="border-t border-sidebar-border" />
                )}
                <button
                  onClick={() => handleSelectThread(thread.id)}
                  className={cn(
                    "w-full text-left px-4 py-3 transition-colors",
                    currentThreadId === thread.id
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "hover:bg-sidebar-accent/50 text-muted-foreground hover:text-foreground"
                  )}
                >
                  <div className="flex items-start gap-2">
                    <MessageSquare className="h-4 w-4 mt-0.5 shrink-0 opacity-50" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">
                        {thread.title || "Untitled"}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {formatDate(thread.created_at)}
                      </p>
                    </div>
                  </div>
                </button>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

export default ThreadSidebar;
