import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getAgents, getAgent } from "@/lib/api";

/**
 * Hook to fetch all agents.
 * Follows Mastra's pattern for consistent state management.
 */
export const useAgents = () => {
  return useQuery({
    queryKey: ["agents"],
    queryFn: () => getAgents(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 1,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to fetch a single agent by ID.
 * Follows Mastra's pattern for consistent state management.
 */
export const useAgent = (agentId?: string) => {
  return useQuery({
    queryKey: ["agent", agentId],
    queryFn: () => (agentId ? getAgent(agentId) : null),
    enabled: Boolean(agentId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 1,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to invalidate agents cache.
 * Useful for refreshing agent list after mutations.
 */
export const useInvalidateAgents = () => {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["agents"] });
  };
};
