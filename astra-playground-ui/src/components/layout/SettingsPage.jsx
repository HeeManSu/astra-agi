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
import { getAgents, getTeams, checkHealth, getAuthToken } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Server, RefreshCw, CheckCircle, XCircle } from "lucide-react";

function SettingsPage() {
  const dispatch = useAppDispatch();
  const { serverUrl, isConnected, isConnecting, connectionError } =
    useAppSelector((state) => state.app);

  const [localServerUrl, setLocalServerUrl] = useState(serverUrl);

  // Connect to server - auto fetch token
  const handleConnect = async () => {
    dispatch(setConnecting(true));
    dispatch(setServerUrl(localServerUrl));

    try {
      // First check if server is reachable
      const healthy = await checkHealth(localServerUrl, null);
      if (!healthy) {
        throw new Error("Server not responding");
      }

      // Try to get auth token (will fail if auth not enabled on server)
      let token = null;
      try {
        const tokenResponse = await getAuthToken(localServerUrl);
        token = tokenResponse.access_token; // API returns 'access_token'
        dispatch(setApiKey(token));
      } catch {
        // Auth may not be enabled, continue without token
        dispatch(setApiKey(""));
      }

      // Fetch agents and teams
      const [agentsData, teamsData] = await Promise.all([
        getAgents(localServerUrl, token).catch(() => []),
        getTeams(localServerUrl, token).catch(() => []),
      ]);

      dispatch(setAgents(agentsData));
      dispatch(setTeams(teamsData));
      dispatch(setConnected(true));
    } catch (error) {
      dispatch(setConnectionError(error.message));
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-background h-full overflow-hidden">
      {/* Header */}
      <div className="px-8 py-6 border-b border-border">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Server className="h-6 w-6" />
          Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Configure your Astra Runtime server connection
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl space-y-8">
          {/* Server Connection */}
          <div>
            <h2 className="text-lg font-semibold mb-4">Server Connection</h2>

            <div className="space-y-4">
              {/* Server URL */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Server URL</label>
                <Input
                  value={localServerUrl}
                  onChange={(e) => setLocalServerUrl(e.target.value)}
                  placeholder="http://localhost:7777"
                  className="max-w-md"
                />
                <p className="text-xs text-muted-foreground">
                  The URL of your running Astra Runtime server
                </p>
              </div>

              {/* Connect Button & Status */}
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
                    <CheckCircle className="h-4 w-4" />
                    Connected
                  </span>
                )}

                {connectionError && (
                  <span className="text-sm text-destructive flex items-center gap-1">
                    <XCircle className="h-4 w-4" />
                    {connectionError}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Info */}
          {isConnected && (
            <div className="p-4 bg-muted rounded-lg">
              <h3 className="text-sm font-medium mb-2">Authentication</h3>
              <p className="text-xs text-muted-foreground">
                Token is automatically fetched when connecting. If the server
                has authentication enabled (jwt_secret configured), all API
                requests will be authenticated automatically.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
