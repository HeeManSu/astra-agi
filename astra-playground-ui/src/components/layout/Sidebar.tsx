import { useState } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  setAgents,
  setTeams,
  setSelectedItem,
  setActiveTab,
} from "@/store/slices/appSlice";
import { setCurrentSession } from "@/store/slices/chatSlice";
import { getAgents, getTeams } from "@/api/client";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Bot,
  Users,
  Settings,
  RefreshCw,
  Wifi,
  WifiOff,
  ChevronRight,
  ChevronDown,
  Folder,
  Wrench,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Agent, Team } from "@/types/api";
import type { SelectedItemType, SessionKey } from "@/types/domain";

function Sidebar() {
  const dispatch = useAppDispatch();
  const {
    serverUrl,
    apiKey,
    agents,
    teams,
    isConnected,
    connectionError,
    selectedItem,
    activeTab,
  } = useAppSelector((state) => state.app);

  const [agentsOpen, setAgentsOpen] = useState(true);
  const [teamsOpen, setTeamsOpen] = useState(true);

  const handleRefresh = async () => {
    if (!isConnected) return;
    try {
      const [agentsData, teamsData] = await Promise.all([
        getAgents(serverUrl, apiKey).catch((): Agent[] => []),
        getTeams(serverUrl, apiKey).catch((): Team[] => []),
      ]);
      dispatch(setAgents(agentsData));
      dispatch(setTeams(teamsData));
    } catch (error) {
      console.error("Failed to refresh:", error);
    }
  };

  const handleSelectItem = (type: SelectedItemType, item: Agent | Team) => {
    const itemId = item.id || item.name;
    dispatch(setSelectedItem({ type, id: itemId, data: { ...item } }));
    const sessionKey: SessionKey = `${type}:${itemId}`;
    dispatch(setCurrentSession(sessionKey));
    if (
      activeTab === "settings" ||
      activeTab === "telemetry" ||
      activeTab === "tools"
    ) {
      dispatch(setActiveTab(type === "agent" ? "agents" : "teams"));
    }
  };

  const handleOpenSettings = () => {
    dispatch(setSelectedItem(null));
    dispatch(setActiveTab("settings"));
  };

  const handleOpenTelemetry = () => {
    dispatch(setSelectedItem(null));
    dispatch(setActiveTab("telemetry"));
  };

  return (
    <div className="w-64 h-full bg-sidebar border-r border-sidebar-border flex flex-col">
      <div className="px-4 py-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2 text-sm">
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-green-500" />
              <span className="text-green-600">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Not connected</span>
            </>
          )}
          {isConnected && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 ml-auto"
              onClick={handleRefresh}
            >
              <RefreshCw className="h-3 w-3" />
            </Button>
          )}
        </div>
        {connectionError && (
          <p className="text-xs text-destructive mt-1">{connectionError}</p>
        )}
      </div>

      <ScrollArea className="flex-1 p-2">
        <div className="space-y-4">
          <Collapsible
            open={agentsOpen}
            onOpenChange={setAgentsOpen}
            className="space-y-1"
          >
            <CollapsibleTrigger className="flex items-center w-full p-2 text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/50 rounded-md group">
              {agentsOpen ? (
                <ChevronDown className="h-4 w-4 mr-2 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-2 text-muted-foreground" />
              )}
              <Bot className="h-4 w-4 mr-2" />
              Agents
              <span className="ml-auto text-xs text-muted-foreground">
                {agents.length}
              </span>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="pl-6 space-y-1">
                {agents.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-2 px-2">
                    {isConnected ? "No agents found" : "Connect to view"}
                  </p>
                ) : (
                  agents.map((agent) => (
                    <button
                      key={agent.id || agent.name}
                      onClick={() => handleSelectItem("agent", agent)}
                      className={cn(
                        "w-full text-left px-2 py-1.5 rounded-md text-sm transition-colors",
                        selectedItem?.type === "agent" &&
                          selectedItem?.id === (agent.id || agent.name)
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/50",
                      )}
                    >
                      <div className="truncate">{agent.name}</div>
                    </button>
                  ))
                )}
              </div>
            </CollapsibleContent>
          </Collapsible>

          <Collapsible
            open={teamsOpen}
            onOpenChange={setTeamsOpen}
            className="space-y-1"
          >
            <CollapsibleTrigger className="flex items-center w-full p-2 text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/50 rounded-md group">
              {teamsOpen ? (
                <ChevronDown className="h-4 w-4 mr-2 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-2 text-muted-foreground" />
              )}
              <Users className="h-4 w-4 mr-2" />
              Teams
              <span className="ml-auto text-xs text-muted-foreground">
                {teams.length}
              </span>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="pl-6 space-y-1">
                {teams.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-2 px-2">
                    {isConnected ? "No teams found" : "Connect to view"}
                  </p>
                ) : (
                  teams.map((team) => (
                    <button
                      key={team.id || team.name}
                      onClick={() => handleSelectItem("team", team)}
                      className={cn(
                        "w-full text-left px-2 py-1.5 rounded-md text-sm transition-colors",
                        selectedItem?.type === "team" &&
                          selectedItem?.id === (team.id || team.name)
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/50",
                      )}
                    >
                      <div className="truncate">{team.name}</div>
                    </button>
                  ))
                )}
              </div>
            </CollapsibleContent>
          </Collapsible>

          <Collapsible className="space-y-1">
            <CollapsibleTrigger className="flex items-center w-full p-2 text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/50 rounded-md group">
              <ChevronRight className="h-4 w-4 mr-2 text-muted-foreground" />
              <Folder className="h-4 w-4 mr-2" />
              Projects
              <span className="ml-auto text-xs text-muted-foreground">0</span>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="pl-6 space-y-1">
                <p className="text-xs text-muted-foreground py-2 px-2">
                  Coming soon
                </p>
              </div>
            </CollapsibleContent>
          </Collapsible>

          <button
            onClick={() => {
              dispatch(setSelectedItem(null));
              dispatch(setActiveTab("tools"));
            }}
            className={cn(
              "flex items-center w-full p-2 text-sm font-medium hover:bg-sidebar-accent/50 rounded-md group",
              activeTab === "tools"
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground",
            )}
          >
            <Wrench className="h-4 w-4 mr-2" />
            Tools
          </button>
        </div>
      </ScrollArea>

      <div className="border-t border-sidebar-border p-2 space-y-1">
        <button
          onClick={handleOpenTelemetry}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors",
            activeTab === "telemetry"
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/50",
          )}
        >
          <Activity className="h-4 w-4" />
          Telemetry
        </button>
        <button
          onClick={handleOpenSettings}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors",
            activeTab === "settings"
              ? "bg-sidebar-accent text-sidebar-accent-foreground"
              : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/50",
          )}
        >
          <Settings className="h-4 w-4" />
          Settings
        </button>
      </div>
    </div>
  );
}

export default Sidebar;
