import { configureStore } from "@reduxjs/toolkit";
import appReducer from "./slices/appSlice";
import chatReducer from "./slices/chatSlice";
import threadReducer from "./slices/threadSlice";

import telemetryReducer from "./slices/telemetrySlice";

export const store = configureStore({
  reducer: {
    app: appReducer,
    chat: chatReducer,
    threads: threadReducer,
    telemetry: telemetryReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export default store;
