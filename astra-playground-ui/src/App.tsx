import { Provider } from "react-redux";
import { Toaster } from "sonner";
import store from "@/store";
import { useAppSelector } from "@/store/hooks";
import Sidebar from "@/components/layout/Sidebar";
import ThreadSidebar from "@/components/layout/ThreadSidebar";
import ChatArea from "@/components/chat/ChatArea";
import SettingsPage from "@/components/layout/SettingsPage";
import TelemetryPage from "@/components/telemetry/TelemetryPage";
import ToolsPage from "@/components/tools/ToolsPage";
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

function MainPanel() {
  const activeTab = useAppSelector((state) => state.app.activeTab);

  switch (activeTab) {
    case "settings":
      return <SettingsPage />;
    case "telemetry":
      return <TelemetryPage />;
    case "tools":
      return <ToolsPage />;
    case "agents":
    case "teams":
    default:
      return <ChatArea />;
  }
}

function AppContent() {
  const activeTab = useAppSelector((state) => state.app.activeTab);
  const selectedItem = useAppSelector((state) => state.app.selectedItem);

  const showThreadSidebar =
    selectedItem !== null &&
    activeTab !== "settings" &&
    activeTab !== "telemetry" &&
    activeTab !== "tools";

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        {showThreadSidebar && <ThreadSidebar />}
        <MainPanel />
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
