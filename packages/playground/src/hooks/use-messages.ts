import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getMessages } from "@/lib/api";

/**
 * Hook to fetch messages for a thread.
 * Follows Mastra's pattern for consistent state management.
 */
export const useMessages = (threadId?: string) => {
  return useQuery({
    queryKey: ["messages", threadId],
    queryFn: () => (threadId ? getMessages(threadId) : null),
    enabled: Boolean(threadId),
    staleTime: 0, // Always fetch fresh messages
    gcTime: 0, // Don't cache messages
    retry: false,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to invalidate messages cache.
 * Useful for refreshing messages after sending a new message.
 */
export const useInvalidateMessages = () => {
  const queryClient = useQueryClient();
  return (threadId?: string) => {
    if (threadId) {
      queryClient.invalidateQueries({ queryKey: ["messages", threadId] });
    }
  };
};
