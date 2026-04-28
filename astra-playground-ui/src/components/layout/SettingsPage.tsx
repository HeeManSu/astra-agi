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
import type { Agent, Team } from "@/types/api";

function SettingsPage() {
  const dispatch = useAppDispatch();
  const { serverUrl, isConnected, isConnecting, connectionError } =
    useAppSelector((state) => state.app);

  const [localServerUrl, setLocalServerUrl] = useState(serverUrl);

  const handleConnect = async () => {
    dispatch(setConnecting(true));
    dispatch(setServerUrl(localServerUrl));

    try {
      const healthy = await checkHealth(localServerUrl, "");
      if (!healthy) {
        throw new Error("Server not responding");
      }

      let token = "";
      try {
        const tokenResponse = await getAuthToken(localServerUrl);
        token = tokenResponse.access_token;
        dispatch(setApiKey(token));
      } catch {
        dispatch(setApiKey(""));
      }

      const [agentsData, teamsData] = await Promise.all([
        getAgents(localServerUrl, token).catch((): Agent[] => []),
        getTeams(localServerUrl, token).catch((): Team[] => []),
      ]);

      dispatch(setAgents(agentsData));
      dispatch(setTeams(teamsData));
      dispatch(setConnected(true));
    } catch (error) {
      dispatch(
        setConnectionError(
          error instanceof Error ? error.message : "Unknown error",
        ),
      );
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-background h-full overflow-hidden">
      <div className="px-8 py-6 border-b border-border">
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Server className="h-6 w-6" />
          Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Configure your Astra Runtime server connection
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl space-y-8">
          <div>
            <h2 className="text-lg font-semibold mb-4">Server Connection</h2>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Server URL</label>
                <Input
                  value={localServerUrl}
                  onChange={(e) => setLocalServerUrl(e.target.value)}
                  placeholder="http://127.0.0.1:8000"
                  className="max-w-md"
                />
                <p className="text-xs text-muted-foreground">
                  The URL of your running Astra Runtime server
                </p>
              </div>

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
