import { useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { useAppSelector } from "../../store/hooks";
import WikiSidebar from "./WikiSidebar";
import WikiContent from "./WikiContent";
import RepoInput from "./RepoInput";

/**
 * WikiPage - Main container for the Wiki tab
 * Uses serverUrl from app state to call the backend API
 */
export default function WikiPage() {
  const [pages, setPages] = useState([]);
  const [selectedPage, setSelectedPage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [repoPath, setRepoPath] = useState("");

  // Get serverUrl from app state (same pattern as other components)
  const { serverUrl, apiKey } = useAppSelector((state) => state.app);

  // Create headers with optional auth
  const createHeaders = () => {
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }
    return headers;
  };

  // Load wiki pages from API
  const loadPages = async () => {
    if (!repoPath || !serverUrl) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${serverUrl}/api/wiki/pages?repo=${encodeURIComponent(repoPath)}`,
        { headers: createHeaders() },
      );
      if (!response.ok) {
        throw new Error("Failed to load wiki pages");
      }
      const data = await response.json();
      setPages(data.pages || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load page content when selected
  const handleSelectPage = async (page) => {
    if (!serverUrl) return;

    setSelectedPage({ ...page, loading: true });

    try {
      const response = await fetch(
        `${serverUrl}/api/wiki/pages/${encodeURIComponent(page.id || page.title)}?repo=${encodeURIComponent(repoPath)}`,
        { headers: createHeaders() },
      );
      if (!response.ok) {
        throw new Error("Failed to load page content");
      }
      const data = await response.json();
      setSelectedPage({ ...page, content: data.content, loading: false });
    } catch (err) {
      setSelectedPage({ ...page, error: err.message, loading: false });
    }
  };

  // Generate wiki for repo
  const handleGenerateWiki = async (path) => {
    if (!serverUrl) {
      setError("Not connected to server");
      return;
    }

    setRepoPath(path);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${serverUrl}/api/wiki/generate`, {
        method: "POST",
        headers: createHeaders(),
        body: JSON.stringify({ repo_path: path }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate wiki");
      }

      // Reload pages after generation
      await loadPages();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
      {/* Header with repo input */}
      <div className="p-4 border-b border-zinc-800 bg-zinc-900/50">
        <RepoInput
          value={repoPath}
          onChange={setRepoPath}
          onGenerate={handleGenerateWiki}
          loading={loading}
        />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <WikiSidebar
          pages={pages}
          selectedPage={selectedPage}
          onSelectPage={handleSelectPage}
        />

        {/* Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-red-400 mb-2">{error}</div>
                <button
                  onClick={loadPages}
                  className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </button>
              </div>
            </div>
          ) : selectedPage?.loading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
            </div>
          ) : selectedPage?.error ? (
            <div className="flex-1 flex items-center justify-center text-red-400">
              {selectedPage.error}
            </div>
          ) : (
            <WikiContent
              title={selectedPage?.title}
              content={selectedPage?.content}
            />
          )}
        </div>
      </div>
    </div>
  );
}
