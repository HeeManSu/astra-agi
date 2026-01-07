import { createContext, useContext, useState, ReactNode, useMemo } from "react";

export interface AgentSettings {
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

interface AgentSettingsContextType {
  settings: AgentSettings;
  updateSettings: (updates: Partial<AgentSettings>) => void;
  resetSettings: () => void;
}

const defaultSettings: AgentSettings = {
  temperature: 0.7,
  maxTokens: undefined,
  stream: true,
};

const AgentSettingsContext = createContext<
  AgentSettingsContextType | undefined
>(undefined);

export function AgentSettingsProvider({
  children,
  defaultSettings: initialSettings,
}: {
  children: ReactNode;
  agentId: string;
  defaultSettings?: AgentSettings;
}) {
  const [settings, setSettings] = useState<AgentSettings>(
    initialSettings || defaultSettings
  );

  const updateSettings = (updates: Partial<AgentSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  const resetSettings = () => {
    setSettings(initialSettings || defaultSettings);
  };

  const value = useMemo(
    () => ({
      settings,
      updateSettings,
      resetSettings,
    }),
    [settings]
  );

  return (
    <AgentSettingsContext.Provider value={value}>
      {children}
    </AgentSettingsContext.Provider>
  );
}

export function useAgentSettings() {
  const context = useContext(AgentSettingsContext);
  if (context === undefined) {
    throw new Error(
      "useAgentSettings must be used within AgentSettingsProvider"
    );
  }
  return context;
}
