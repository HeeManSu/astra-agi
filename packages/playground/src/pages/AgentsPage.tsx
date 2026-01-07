import { Link } from "react-router-dom";
import { Bot, Search, ArrowRight, Wrench } from "lucide-react";
import { useState } from "react";
import { useAgents } from "@/hooks/use-agents";

export function AgentsPage() {
  const [search, setSearch] = useState("");
  const { data: agents, isLoading, error } = useAgents();

  const filteredAgents = agents?.filter(
    (agent) =>
      agent.name.toLowerCase().includes(search.toLowerCase()) ||
      agent.description?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold">Agents</h1>
        </div>
        <a
          href="https://astra.dev/docs/agents"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Agents documentation
        </a>
      </header>

      {/* Search */}
      <div className="border-b border-border px-6 py-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search agents"
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
      <div className="grid grid-cols-[1fr_1.5fr_1fr] gap-4 border-b border-border px-6 py-3 text-xs font-medium uppercase text-muted-foreground">
        <span>Name</span>
        <span>Model</span>
        <span>Tools</span>
      </div>

      {/* Agent List */}
      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-12 text-destructive">
            <p className="text-sm">Failed to load agents</p>
            <p className="text-xs text-muted-foreground">
              {(error as Error).message}
            </p>
          </div>
        )}

        {filteredAgents?.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Bot className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-sm">No agents found</p>
          </div>
        )}

        {filteredAgents?.map((agent) => (
          <Link
            key={agent.id}
            to={`/agents/${agent.id}`}
            className="group grid grid-cols-[1fr_1.5fr_1fr] gap-4 border-b border-border px-6 py-4 transition-colors hover:bg-secondary"
          >
            {/* Name */}
            <div>
              <p className="font-medium text-foreground">{agent.name}</p>
              <p className="text-sm text-muted-foreground line-clamp-1">
                {agent.description || "No description"}
              </p>
            </div>

            {/* Model */}
            <div className="flex items-center">
              <span className="rounded-full bg-secondary px-3 py-1 text-xs text-muted-foreground font-mono">
                {agent.model || "unknown"}
              </span>
            </div>

            {/* Attached Entities */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-sm">
                <Wrench className="h-4 w-4 text-amber-500" />
                <span className="text-muted-foreground">
                  {agent.tools} {agent.tools === 1 ? "tool" : "tools"}
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
