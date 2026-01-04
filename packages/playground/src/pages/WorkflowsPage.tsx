import { GitBranch } from "lucide-react";

export function WorkflowsPage() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-center gap-2">
          <GitBranch className="h-5 w-5 text-blue-500" />
          <h1 className="text-lg font-semibold">Workflows</h1>
        </div>
        <a
          href="https://astra.dev/docs/workflows"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          Workflows documentation
        </a>
      </header>

      {/* Empty State */}
      <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
        <GitBranch className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm">No workflows registered</p>
        <p className="text-xs">
          Workflows will appear here when they are created
        </p>
      </div>
    </div>
  );
}
