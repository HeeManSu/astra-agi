import { configureStore } from "@reduxjs/toolkit";
import appReducer from "./slices/appSlice";
import chatReducer from "./slices/chatSlice";
import threadReducer from "./slices/threadSlice";

export const store = configureStore({
  reducer: {
    app: appReducer,
    chat: chatReducer,
    threads: threadReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export default store;
