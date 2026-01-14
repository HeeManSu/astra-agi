import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getTeams, getTeam } from "@/lib/api";

/**
 * Hook to fetch all teams.
 * Follows the same pattern as use-agents.ts.
 */
export const useTeams = () => {
  return useQuery({
    queryKey: ["teams"],
    queryFn: () => getTeams(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 1,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to fetch a single team by ID.
 */
export const useTeam = (teamId?: string) => {
  return useQuery({
    queryKey: ["team", teamId],
    queryFn: () => (teamId ? getTeam(teamId) : null),
    enabled: Boolean(teamId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: 1,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook to invalidate teams cache.
 * Useful for refreshing team list after mutations.
 */
export const useInvalidateTeams = () => {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["teams"] });
  };
};
