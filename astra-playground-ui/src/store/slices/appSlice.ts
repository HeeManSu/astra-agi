import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { Agent, Team } from "@/types/api";
import type { ActiveTab, SelectedItem } from "@/types/domain";
import { loadPersistedSettings } from "@/store/middleware/persistAppSettings";

export interface AppState {
  serverUrl: string;
  apiKey: string;
  isConnected: boolean;
  isConnecting: boolean;
  connectionError: string | null;

  agents: Agent[];
  teams: Team[];

  selectedItem: SelectedItem | null;
  sidebarOpen: boolean;
  activeTab: ActiveTab;
}

const persisted = loadPersistedSettings();

const initialState: AppState = {
  serverUrl: persisted.serverUrl ?? "http://127.0.0.1:8000",
  apiKey: persisted.apiKey ?? "",
  isConnected: false,
  isConnecting: false,
  connectionError: null,

  agents: [],
  teams: [],

  selectedItem: null,
  sidebarOpen: true,
  activeTab: "agents",
};

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    setServerUrl: (state, action: PayloadAction<string>) => {
      state.serverUrl = action.payload;
    },
    setApiKey: (state, action: PayloadAction<string>) => {
      state.apiKey = action.payload;
    },
    setConnecting: (state, action: PayloadAction<boolean>) => {
      state.isConnecting = action.payload;
    },
    setConnected: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
      state.isConnecting = false;
      state.connectionError = null;
    },
    setConnectionError: (state, action: PayloadAction<string | null>) => {
      state.connectionError = action.payload;
      state.isConnected = false;
      state.isConnecting = false;
    },
    setAgents: (state, action: PayloadAction<Agent[]>) => {
      state.agents = action.payload;
    },
    setTeams: (state, action: PayloadAction<Team[]>) => {
      state.teams = action.payload;
    },
    setSelectedItem: (state, action: PayloadAction<SelectedItem | null>) => {
      state.selectedItem = action.payload;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
    setActiveTab: (state, action: PayloadAction<ActiveTab>) => {
      state.activeTab = action.payload;
    },
    clearConnection: (state) => {
      state.isConnected = false;
      state.agents = [];
      state.teams = [];
      state.selectedItem = null;
    },
  },
});

export const {
  setServerUrl,
  setApiKey,
  setConnecting,
  setConnected,
  setConnectionError,
  setAgents,
  setTeams,
  setSelectedItem,
  setSidebarOpen,
  setActiveTab,
  clearConnection,
} = appSlice.actions;

export default appSlice.reducer;
