import { Link } from "react-router-dom";
import { Users, Search, ArrowRight } from "lucide-react";
import { useState } from "react";
import { useTeams } from "@/hooks/use-teams";

export function TeamsPage() {
  const [search, setSearch] = useState("");
  const { data: teams, isLoading, error } = useTeams();

  const filteredTeams = teams?.filter(
    (team) =>
      team.name.toLowerCase().includes(search.toLowerCase()) ||
      team.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold">Teams</h1>
        </div>
        <a
          href="https://astra.dev/docs/teams"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Teams documentation
        </a>
      </header>

      {/* Search */}
      <div className="border-b border-border px-6 py-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search teams"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-border bg-input py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
            ↵ Enter
          </span>
        </div>
      </div>

      {/* Table Header */}
      <div className="grid grid-cols-[1fr_1fr_1fr] gap-4 border-b border-border px-6 py-3 text-xs font-medium uppercase text-muted-foreground">
        <span>Name</span>
        <span>Model</span>
        <span>Members</span>
      </div>

      {/* Team List */}
      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-12 text-destructive">
            <p className="text-sm">Failed to load teams</p>
            <p className="text-xs text-muted-foreground">
              {(error as Error).message}
            </p>
          </div>
        )}

        {filteredTeams?.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Users className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-sm">No teams found</p>
          </div>
        )}

        {filteredTeams?.map((team) => (
          <Link
            key={team.id}
            to={`/teams/${team.id}`}
            className="group grid grid-cols-[1fr_1fr_1fr] gap-4 border-b border-border px-6 py-4 transition-colors hover:bg-secondary"
          >
            {/* Name */}
            <div>
              <p className="font-medium text-foreground">{team.name}</p>
              <p className="text-sm text-muted-foreground line-clamp-1">
                {team.description || "No description"}
              </p>
            </div>

            {/* Model */}
            <div className="flex items-center">
              <span className="rounded-full bg-secondary px-3 py-1 text-xs text-muted-foreground font-mono">
                {team.model || "unknown"}
              </span>
            </div>

            {/* Members */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-sm">
                <Users className="h-4 w-4 text-blue-500" />
                <span className="text-muted-foreground">
                  {team.member_count}{" "}
                  {team.member_count === 1 ? "member" : "members"}
                </span>
              </div>
              <ArrowRight className="ml-auto h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
