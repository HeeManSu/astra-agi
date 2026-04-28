/**
 * Wraps `react-markdown` with a Mermaid-aware code block and Prism syntax
 * highlighting. Memoized component map so identity stays stable across renders.
 */

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import Markdown, { type Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
});

interface MermaidDiagramProps {
  code: string;
}

function MermaidDiagram({ code }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`;
        const result = await mermaid.render(id, code);
        setSvg(result.svg);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Render failed");
      }
    };
    if (code) void renderDiagram();
  }, [code]);

  if (error) {
    return (
      <div className="p-3 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">
        Mermaid Error: {error}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-4 p-4 bg-muted/50 rounded-lg overflow-x-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

interface CodeBlockProps {
  className?: string;
  children?: ReactNode;
}

function CodeBlock({ className, children, ...props }: CodeBlockProps) {
  const match = /language-(\w+)/.exec(className ?? "");
  const language = match ? match[1] : "";
  const code = String(children ?? "").replace(/\n$/, "");

  if (language === "mermaid") {
    return <MermaidDiagram code={code} />;
  }

  if (match) {
    return (
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        PreTag="div"
        className="rounded-lg !my-3 text-sm"
        {...props}
      >
        {code}
      </SyntaxHighlighter>
    );
  }

  return (
    <code
      className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono"
      {...props}
    >
      {children}
    </code>
  );
}

const markdownComponents = {
  code: CodeBlock as NonNullable<Components["code"]>,
  pre: ({ children }: { children?: ReactNode }) => <>{children}</>,
} satisfies Components;

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="prose prose-invert prose-sm max-w-none">
      <Markdown components={markdownComponents}>{content}</Markdown>
    </div>
  );
}
