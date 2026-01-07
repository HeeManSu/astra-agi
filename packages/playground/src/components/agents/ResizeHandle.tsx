import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ResizeHandleProps {
  side: "left" | "right";
  onToggle: () => void;
  isCollapsed: boolean;
  className?: string;
}

export function ResizeHandle({
  side,
  onToggle,
  isCollapsed,
  className,
}: ResizeHandleProps) {
  return (
    <div
      className={cn(
        "group relative flex items-center justify-center cursor-col-resize hover:bg-border/50 transition-colors",
        side === "left" ? "border-r border-border" : "border-l border-border",
        className
      )}
      onDoubleClick={onToggle}
    >
      {/* Hover indicator with arrow */}
      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        {side === "left" ? (
          <ChevronLeft
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform",
              isCollapsed && "rotate-180"
            )}
          />
        ) : (
          <ChevronRight
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform",
              isCollapsed && "rotate-180"
            )}
          />
        )}
      </div>

      {/* Invisible drag area */}
      <div className="absolute inset-0 w-1 cursor-col-resize" />
    </div>
  );
}
