import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { AgentsPage } from "./pages/AgentsPage";
import { AgentChatPage } from "./pages/AgentChatPage";
import { ToolsPage } from "./pages/ToolsPage";
import { WorkflowsPage } from "./pages/WorkflowsPage";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/agents" replace />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/agents/:agentId" element={<AgentChatPage />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/workflows" element={<WorkflowsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
