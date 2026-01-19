import { configureStore } from "@reduxjs/toolkit";
import appReducer from "./slices/appSlice";
import chatReducer from "./slices/chatSlice";

export const store = configureStore({
  reducer: {
    app: appReducer,
    chat: chatReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
});

export default store;
