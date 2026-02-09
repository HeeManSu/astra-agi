import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  FileText,
  FolderOpen,
  Folder,
} from "lucide-react";

/**
 * WikiSidebar - Tree navigation for wiki pages
 */
export default function WikiSidebar({ pages, selectedPage, onSelectPage }) {
  return (
    <div className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-zinc-800">
        <h2 className="font-semibold text-white flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-400" />
          Wiki Pages
        </h2>
      </div>

      <div className="flex-1 overflow-auto p-2">
        {pages && pages.length > 0 ? (
          <PageTree
            pages={pages}
            selectedPage={selectedPage}
            onSelectPage={onSelectPage}
          />
        ) : (
          <div className="text-sm text-zinc-500 p-2">
            No wiki pages yet. Generate a wiki first.
          </div>
        )}
      </div>
    </div>
  );
}

function PageTree({ pages, selectedPage, onSelectPage, depth = 0 }) {
  return (
    <ul className="space-y-0.5">
      {pages.map((page) => (
        <PageTreeItem
          key={page.id || page.title}
          page={page}
          selectedPage={selectedPage}
          onSelectPage={onSelectPage}
          depth={depth}
        />
      ))}
    </ul>
  );
}

function PageTreeItem({ page, selectedPage, onSelectPage, depth }) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = page.children && page.children.length > 0;
  const isSelected =
    selectedPage?.id === page.id || selectedPage?.title === page.title;

  return (
    <li>
      <div
        className={`flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors ${
          isSelected
            ? "bg-blue-600/20 text-blue-400"
            : "text-zinc-300 hover:bg-zinc-800"
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => {
          if (hasChildren) {
            setExpanded(!expanded);
          }
          onSelectPage(page);
        }}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="w-3 h-3 text-zinc-500 shrink-0" />
          ) : (
            <ChevronRight className="w-3 h-3 text-zinc-500 shrink-0" />
          )
        ) : (
          <span className="w-3" />
        )}

        {hasChildren ? (
          expanded ? (
            <FolderOpen className="w-4 h-4 text-yellow-500 shrink-0" />
          ) : (
            <Folder className="w-4 h-4 text-yellow-500 shrink-0" />
          )
        ) : (
          <FileText className="w-4 h-4 text-zinc-400 shrink-0" />
        )}

        <span className="truncate">{page.title}</span>
      </div>

      {hasChildren && expanded && (
        <PageTree
          pages={page.children}
          selectedPage={selectedPage}
          onSelectPage={onSelectPage}
          depth={depth + 1}
        />
      )}
    </li>
  );
}
