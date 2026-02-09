import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

// Initialize mermaid with dark theme support
mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
  fontFamily: "ui-sans-serif, system-ui, sans-serif",
});

let mermaidId = 0;

export default function MermaidDiagram({ chart }) {
  const containerRef = useRef(null);
  const [svg, setSvg] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    const renderChart = async () => {
      if (!chart || !containerRef.current) return;

      try {
        const id = `mermaid-${mermaidId++}`;
        const { svg: renderedSvg } = await mermaid.render(
          id,
          chart.toString().trim(),
        );
        setSvg(renderedSvg);
        setError(null);
      } catch (err) {
        console.error("Mermaid render error:", err);
        setError(err.message || "Failed to render diagram");
      }
    };

    renderChart();
  }, [chart]);

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
        <div className="font-medium mb-1">Diagram Error</div>
        <pre className="text-xs overflow-auto">{error}</pre>
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-red-400">
            Show source
          </summary>
          <pre className="mt-1 text-xs bg-black/30 p-2 rounded overflow-auto">
            {chart}
          </pre>
        </details>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="mermaid-diagram my-4 p-4 bg-zinc-900/50 rounded-lg border border-zinc-700/50 overflow-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
