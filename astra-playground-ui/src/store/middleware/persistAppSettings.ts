import type { Middleware } from "@reduxjs/toolkit";
import type { AppState } from "@/store/slices/appSlice";

const STORAGE_KEY = "astra-settings";

export interface PersistedSettings {
  serverUrl?: string;
  apiKey?: string;
}

export function loadPersistedSettings(): PersistedSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      return parsed as PersistedSettings;
    }
    return {};
  } catch {
    return {};
  }
}

function writePersistedSettings(settings: PersistedSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (err) {
    console.error("Failed to save settings:", err);
  }
}

interface PersistableState {
  app: AppState;
}

/**
 * Persists `app.serverUrl` and `app.apiKey` to localStorage whenever they
 * change. Replaces the impure `setItem` calls that previously lived inside
 * appSlice reducers.
 */
export const persistAppSettings: Middleware<object, PersistableState> =
  (store) => (next) => (action) => {
    const before = store.getState().app;
    const result = next(action);
    const after = store.getState().app;

    if (
      before.serverUrl !== after.serverUrl ||
      before.apiKey !== after.apiKey
    ) {
      writePersistedSettings({
        serverUrl: after.serverUrl,
        apiKey: after.apiKey,
      });
    }

    return result;
  };
