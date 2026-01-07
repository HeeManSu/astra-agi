import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  Bot,
  Wrench,
  GitBranch,
  FileText,
  Github,
  ExternalLink,
  Settings,
  Activity,
  X,
} from "lucide-react";

const navigation = [
  { name: "Agents", href: "/agents", icon: Bot },
  { name: "Workflows", href: "/workflows", icon: GitBranch },
  { name: "Tools", href: "/tools", icon: Wrench },
  { name: "Observability", href: "/observability", icon: Activity },
];

const bottomLinks = [
  { name: "Astra APIs", href: "/api/docs", icon: FileText, external: true },
  {
    name: "Documentation",
    href: "https://astra.dev/docs",
    icon: FileText,
    external: true,
  },
  {
    name: "Github",
    href: "https://github.com/astra-ai/astra",
    icon: Github,
    external: true,
  },
];

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps = {}) {
  return (
    <aside className="flex w-[200px] flex-col border-r border-border bg-card h-full">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Bot className="h-5 w-5 text-primary-foreground" />
        </div>
        <span className="font-semibold text-foreground flex-1">
          Astra Studio
        </span>
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden p-1 text-muted-foreground hover:text-foreground"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* Bottom Links */}
      <div className="border-t border-border p-2">
        {bottomLinks.map((item) => (
          <a
            key={item.name}
            href={item.href}
            target={item.external ? "_blank" : undefined}
            rel={item.external ? "noopener noreferrer" : undefined}
            className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <item.icon className="h-4 w-4" />
            {item.name}
            {item.external && <ExternalLink className="ml-auto h-3 w-3" />}
          </a>
        ))}
      </div>

      {/* Settings */}
      <div className="border-t border-border p-2">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            )
          }
        >
          <Settings className="h-4 w-4" />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
