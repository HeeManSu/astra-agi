import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import MermaidDiagram from "@/components/ui/MermaidDiagram";

/**
 * WikiContent - Renders markdown content with Mermaid diagram support
 */
export default function WikiContent({ content, title }) {
  if (!content) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-500">
        Select a wiki page to view
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-6">
      {title && (
        <h1 className="text-2xl font-bold text-white mb-6 pb-4 border-b border-zinc-700">
          {title}
        </h1>
      )}

      <article className="prose prose-invert prose-zinc max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // Custom code block handler for Mermaid
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const language = match ? match[1] : "";

              // Render Mermaid diagrams
              if (language === "mermaid" && !inline) {
                return <MermaidDiagram chart={String(children)} />;
              }

              // Regular code blocks with syntax highlighting
              if (!inline && language) {
                return (
                  <pre
                    className={`language-${language} bg-zinc-900 rounded-lg p-4 overflow-auto`}
                  >
                    <code className={className} {...props}>
                      {children}
                    </code>
                  </pre>
                );
              }

              // Inline code
              return (
                <code
                  className="bg-zinc-800 px-1.5 py-0.5 rounded text-pink-400"
                  {...props}
                >
                  {children}
                </code>
              );
            },

            // Enhanced table styling
            table({ children }) {
              return (
                <div className="overflow-auto my-4">
                  <table className="min-w-full border-collapse border border-zinc-700">
                    {children}
                  </table>
                </div>
              );
            },
            th({ children }) {
              return (
                <th className="border border-zinc-700 bg-zinc-800 px-4 py-2 text-left font-semibold">
                  {children}
                </th>
              );
            },
            td({ children }) {
              return (
                <td className="border border-zinc-700 px-4 py-2">{children}</td>
              );
            },

            // Enhanced headings with anchors
            h1({ children }) {
              return (
                <h1 className="text-2xl font-bold mt-8 mb-4 text-white">
                  {children}
                </h1>
              );
            },
            h2({ children }) {
              return (
                <h2 className="text-xl font-semibold mt-6 mb-3 text-zinc-100 border-b border-zinc-700 pb-2">
                  {children}
                </h2>
              );
            },
            h3({ children }) {
              return (
                <h3 className="text-lg font-medium mt-4 mb-2 text-zinc-200">
                  {children}
                </h3>
              );
            },

            // Links
            a({ href, children }) {
              const isExternal = href?.startsWith("http");
              return (
                <a
                  href={href}
                  target={isExternal ? "_blank" : undefined}
                  rel={isExternal ? "noopener noreferrer" : undefined}
                  className="text-blue-400 hover:text-blue-300 underline"
                >
                  {children}
                </a>
              );
            },

            // Blockquotes
            blockquote({ children }) {
              return (
                <blockquote className="border-l-4 border-blue-500 pl-4 my-4 text-zinc-400 italic">
                  {children}
                </blockquote>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </article>
    </div>
  );
}
