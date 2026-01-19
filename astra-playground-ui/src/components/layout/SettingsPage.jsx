import { useState } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  setServerUrl,
  setApiKey,
  setAgents,
  setTeams,
  setConnected,
  setConnecting,
  setConnectionError,
} from "@/store/slices/appSlice";
import { getAgents, getTeams, checkHealth } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Settings,
  KeyRound,
  Server,
  AlertTriangle,
  Eye,
  EyeOff,
  Copy,
  Check,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Generate a random API key
const generateApiKey = () => {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let key = "";
  for (let i = 0; i < 32; i++) {
    key += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `astra_${key}`;
};

function SettingsPage() {
  const dispatch = useAppDispatch();
  const { serverUrl, apiKey, isConnected, isConnecting, connectionError } =
    useAppSelector((state) => state.app);

  const [showApiKey, setShowApiKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [localServerUrl, setLocalServerUrl] = useState(serverUrl);
  const [localApiKey, setLocalApiKey] = useState(apiKey);
  const [keyGeneratedAt, setKeyGeneratedAt] = useState(
    localStorage.getItem("astra-key-generated-at") || null
  );
  const [activeSection, setActiveSection] = useState("server");

  // Connect to server
  const handleConnect = async () => {
    dispatch(setConnecting(true));
    dispatch(setServerUrl(localServerUrl));
    dispatch(setApiKey(localApiKey));

    try {
      const healthy = await checkHealth(localServerUrl, localApiKey);
      if (!healthy) {
        throw new Error("Server not responding");
      }

      const [agentsData, teamsData] = await Promise.all([
        getAgents(localServerUrl, localApiKey).catch(() => []),
        getTeams(localServerUrl, localApiKey).catch(() => []),
      ]);

      dispatch(setAgents(agentsData));
      dispatch(setTeams(teamsData));
      dispatch(setConnected(true));
    } catch (error) {
      dispatch(setConnectionError(error.message));
    }
  };

  // Copy API key
  const handleCopy = () => {
    navigator.clipboard.writeText(localApiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Generate new API key
  const handleGenerateKey = () => {
    const newKey = generateApiKey();
    setLocalApiKey(newKey);
    const now = new Date().toLocaleString();
    setKeyGeneratedAt(now);
    localStorage.setItem("astra-key-generated-at", now);
  };

  return (
    <div className="flex-1 flex flex-col bg-background h-full overflow-hidden">
      {/* Header */}
      <div className="px-8 py-6 border-b border-border">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Settings className="h-6 w-6" />
          Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage your server connection and API keys
        </p>
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Navigation */}
        <div className="w-48 border-r border-border p-4">
          <nav className="space-y-1">
            <button
              onClick={() => setActiveSection("server")}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors",
                activeSection === "server"
                  ? "bg-muted text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <Server className="h-4 w-4" />
              Server
            </button>
            <button
              onClick={() => setActiveSection("api")}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors",
                activeSection === "api"
                  ? "bg-muted text-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <KeyRound className="h-4 w-4" />
              API
            </button>
          </nav>
        </div>

        {/* Right Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {activeSection === "server" && (
            <div className="max-w-4xl">
              <h2 className="text-xl font-semibold">Server Connection</h2>
              <p className="text-muted-foreground mt-1 mb-6">
                Configure your Astra Runtime server connection.
              </p>

              <div className="space-y-6">
                {/* Server URL */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Server URL</label>
                  <Input
                    value={localServerUrl}
                    onChange={(e) => setLocalServerUrl(e.target.value)}
                    placeholder="http://localhost:7777"
                    className="w-full max-w-xl"
                  />
                  <p className="text-xs text-muted-foreground">
                    The URL of your running Astra Runtime server.
                  </p>
                </div>

                {/* Connection Status */}
                <div className="flex items-center gap-4">
                  <Button onClick={handleConnect} disabled={isConnecting}>
                    {isConnecting ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                        Connecting...
                      </>
                    ) : isConnected ? (
                      "Reconnect"
                    ) : (
                      "Connect"
                    )}
                  </Button>
                  {isConnected && (
                    <span className="text-sm text-green-600 flex items-center gap-1">
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                      Connected
                    </span>
                  )}
                  {connectionError && (
                    <span className="text-sm text-destructive">
                      {connectionError}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeSection === "api" && (
            <div className="max-w-4xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">API Keys</h2>
                  <p className="text-muted-foreground mt-1">
                    Generate and manage API keys to authenticate API requests.
                    Keep your keys secure and never share them publicly.
                  </p>
                </div>
                <Button variant="outline" onClick={handleGenerateKey}>
                  <KeyRound className="h-4 w-4 mr-2" />
                  Regenerate
                </Button>
              </div>

              <Separator className="my-6" />

              {/* Warning Banner */}
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                  <div className="text-sm text-amber-800">
                    <strong>Warning:</strong> Keep your API key secure. Do not
                    share it publicly or commit it to version control. If your
                    key is compromised, regenerate it immediately.
                  </div>
                </div>
              </div>

              {/* API Key Display */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Your API Key</label>
                <div className="flex items-center gap-2">
                  <div className="relative flex-1 max-w-xl">
                    <Input
                      type={showApiKey ? "text" : "password"}
                      value={localApiKey}
                      onChange={(e) => setLocalApiKey(e.target.value)}
                      placeholder="Enter or generate an API key..."
                      className="font-mono pr-20"
                    />
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => setShowApiKey(!showApiKey)}
                      >
                        {showApiKey ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={handleCopy}
                        disabled={!localApiKey}
                      >
                        {copied ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
                {keyGeneratedAt && (
                  <p className="text-xs text-muted-foreground">
                    Generated on {keyGeneratedAt}
                  </p>
                )}
              </div>

              {/* Usage Instructions */}
              <div className="mt-8 p-4 bg-muted rounded-lg">
                <h3 className="text-sm font-medium mb-2">Usage</h3>
                <p className="text-xs text-muted-foreground mb-3">
                  Include this API key in your requests to the Astra Runtime:
                </p>
                <pre className="text-xs bg-background p-3 rounded border overflow-x-auto">
                  {`curl -X POST http://localhost:7777/agents/my-agent/invoke \\
  -H "Authorization: Bearer ${localApiKey || "<your-api-key>"}" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello!"}'`}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
