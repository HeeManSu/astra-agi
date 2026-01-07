import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { AuthProvider } from "./components/auth/AuthProvider";
import { AgentsPage } from "./pages/AgentsPage";
import { AgentChatPage } from "./pages/AgentChatPage";
import { ToolsPage } from "./pages/ToolsPage";
import { WorkflowsPage } from "./pages/WorkflowsPage";
import { SettingsPage } from "./pages/SettingsPage";

function App() {
  return (
    <AuthProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/agents" replace />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/agents/:agentId" element={<AgentChatPage />} />
          <Route path="/agents/:agentId/chat/:threadId" element={<AgentChatPage />} />
          <Route path="/tools" element={<ToolsPage />} />
          <Route path="/workflows" element={<WorkflowsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </AuthProvider>
  );
}

export default App;
