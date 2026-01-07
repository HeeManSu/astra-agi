import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getThreads, createThread, deleteThread } from "@/lib/api";

/**
 * Hook to fetch threads for an agent.
 * Follows Mastra's pattern for consistent state management.
 */
export const useThreads = (agentId?: string) => {
  return useQuery({
    queryKey: ["threads", agentId],
    queryFn: () => (agentId ? getThreads(agentId) : null),
    enabled: Boolean(agentId),
    staleTime: 0, // Always fetch fresh threads
    gcTime: 0, // Don't cache threads
    retry: false,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to create a new thread.
 * Returns mutation function and loading state.
 */
export const useCreateThread = (agentId?: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ title, message }: { title?: string; message?: string }) => {
      if (!agentId) throw new Error("Agent ID is required");
      return createThread(agentId, title, message);
    },
    onSuccess: () => {
      // Invalidate threads list to refresh
      if (agentId) {
        queryClient.invalidateQueries({ queryKey: ["threads", agentId] });
      }
    },
  });
};

/**
 * Hook to delete a thread.
 * Returns mutation function and loading state.
 */
export const useDeleteThread = (agentId?: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (threadId: string) => {
      if (!threadId) throw new Error("Thread ID is required");
      return deleteThread(threadId);
    },
    onSuccess: () => {
      // Invalidate threads list to refresh
      if (agentId) {
        queryClient.invalidateQueries({ queryKey: ["threads", agentId] });
      }
    },
  });
};
