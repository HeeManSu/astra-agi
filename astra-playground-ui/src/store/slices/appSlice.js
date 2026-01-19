import { createSlice } from "@reduxjs/toolkit";

// Load settings from localStorage
const loadSettings = () => {
  try {
    const saved = localStorage.getItem("astra-settings");
    return saved ? JSON.parse(saved) : {};
  } catch {
    return {};
  }
};

const savedSettings = loadSettings();

const initialState = {
  // Server connection
  serverUrl: savedSettings.serverUrl || "http://localhost:7777",
  apiKey: savedSettings.apiKey || "",
  isConnected: false,
  isConnecting: false,
  connectionError: null,

  // Data
  agents: [],
  teams: [],

  // UI State
  selectedItem: null, // { type: 'agent' | 'team', id: string }
  sidebarOpen: true,
  activeTab: "agents", // 'agents' | 'teams' | 'settings'
};

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    setServerUrl: (state, action) => {
      state.serverUrl = action.payload;
      saveSettings(state);
    },
    setApiKey: (state, action) => {
      state.apiKey = action.payload;
      saveSettings(state);
    },
    setConnecting: (state, action) => {
      state.isConnecting = action.payload;
    },
    setConnected: (state, action) => {
      state.isConnected = action.payload;
      state.isConnecting = false;
      state.connectionError = null;
    },
    setConnectionError: (state, action) => {
      state.connectionError = action.payload;
      state.isConnected = false;
      state.isConnecting = false;
    },
    setAgents: (state, action) => {
      state.agents = action.payload;
    },
    setTeams: (state, action) => {
      state.teams = action.payload;
    },
    setSelectedItem: (state, action) => {
      state.selectedItem = action.payload;
    },
    setSidebarOpen: (state, action) => {
      state.sidebarOpen = action.payload;
    },
    setActiveTab: (state, action) => {
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

// Save settings to localStorage
const saveSettings = (state) => {
  try {
    localStorage.setItem(
      "astra-settings",
      JSON.stringify({
        serverUrl: state.serverUrl,
        apiKey: state.apiKey,
      })
    );
  } catch (e) {
    console.error("Failed to save settings:", e);
  }
};

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
