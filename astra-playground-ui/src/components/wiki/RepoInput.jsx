import { useState } from "react";
import { Globe, Loader2, Sparkles } from "lucide-react";

/**
 * RepoInput - Input field for repository URL/path with generate button
 */
export default function RepoInput({ value, onChange, onGenerate, loading }) {
  const [inputValue, setInputValue] = useState(value || "");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onChange(inputValue.trim());
      onGenerate(inputValue.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-3">
      <div className="flex-1 relative">
        <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Enter GitHub URL or local path (e.g., https://github.com/user/repo or /path/to/project)"
          className="w-full pl-10 pr-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          disabled={loading}
        />
      </div>

      <button
        type="submit"
        disabled={loading || !inputValue.trim()}
        className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg font-medium text-sm transition-colors"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Generating...
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4" />
            Generate Wiki
          </>
        )}
      </button>
    </form>
  );
}
