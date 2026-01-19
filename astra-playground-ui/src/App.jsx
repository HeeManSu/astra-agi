import { Provider } from "react-redux";
import { Toaster } from "sonner";
import store from "@/store";
import { useAppSelector } from "@/store/hooks";
import Sidebar from "@/components/layout/Sidebar";
import ThreadSidebar from "@/components/layout/ThreadSidebar";
import ChatArea from "@/components/chat/ChatArea";
import SettingsPage from "@/components/layout/SettingsPage";
import "./index.css";

function Header() {
  return (
    <div className="h-16 bg-black text-white flex items-center px-6 justify-between shrink-0">
      <div className="flex items-center gap-3 font-semibold text-lg">
        <img src="/logo.svg" alt="Astra Logo" className="h-8 w-8" />
        <span>Astra</span>
      </div>
      <div className="text-xs text-zinc-400">v0.1.0</div>
    </div>
  );
}

function AppContent() {
  const { activeTab, selectedItem } = useAppSelector((state) => state.app);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        {/* Thread Sidebar - visible when agent/team is selected */}
        {selectedItem && activeTab !== "settings" && <ThreadSidebar />}
        {activeTab === "settings" ? <SettingsPage /> : <ChatArea />}
      </div>
      <Toaster position="top-right" richColors />
    </div>
  );
}

function App() {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
}

export default App;
