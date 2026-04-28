import { configureStore } from "@reduxjs/toolkit";
import appReducer from "./slices/appSlice";
import chatReducer from "./slices/chatSlice";
import threadReducer from "./slices/threadSlice";
import telemetryReducer from "./slices/telemetrySlice";
import { persistAppSettings } from "./middleware/persistAppSettings";
import { rtkApi } from "@/api/rtkApi";

export const store = configureStore({
  reducer: {
    app: appReducer,
    chat: chatReducer,
    threads: threadReducer,
    telemetry: telemetryReducer,
    [rtkApi.reducerPath]: rtkApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    })
      .concat(rtkApi.middleware)
      .concat(persistAppSettings),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export default store;
