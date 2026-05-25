import { useState } from "react";
import { useTerminalStore } from "../../../store/terminalStore";
import { BookOpen } from "lucide-react";
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Expanded regex covering torque, lockwire, resistance, pressure, clearances, and ISO standards
const COMPLIANCE_REGEX = /(\b\d+(?:\.\d+)?\s*(?:to|and|-)\s*\d+(?:\.\d+)?\s*(?:foot-pounds|inch-pounds|ft-lbs|in-lbs|Nm|milliohms|m\u2126|m\u03a9|ohms|\u2126|PSI|bar|inch|inches|in|mm)\b|\b\d+(?:\.\d+)?\s*(?:foot-pounds|inch-pounds|ft-lbs|in-lbs|Nm|milliohms|m\u2126|m\u03a9|ohms|\u2126|PSI|bar|inch|inches|in|mm)\b|safety wire|lockwire|lock-wire|safety-wire|0\.032|ISO\s*\d+|Class\s+[A-Z]|Rmin\s*=\s*\d+.\w+|\bbend radius\b)/gi;

function highlightAmmText(text: string) {
  if (!text) return "";
  
  const parts = text.split(COMPLIANCE_REGEX);
  return parts.map((part, i) => {
    COMPLIANCE_REGEX.lastIndex = 0;
    if (COMPLIANCE_REGEX.test(part)) {
      return (
        <mark key={i} className="bg-yellow-200 text-gray-900 px-1 rounded font-semibold">
          {part}
        </mark>
      );
    }
    return part;
  });
}

function getFocusedSnippet(text: string): string {
  if (!text) return "";

  // Clean up source headers and page boundary markers before slicing
  const headerMatch = text.match(/^(DOCUMENT SOURCE: [^\n]+\n(?:\.\.\. .*? \[PAGE BOUNDARY\] )?)/i);
  const header = headerMatch ? headerMatch[1] : "";
  const actualText = header ? text.substring(header.length) : text;

  // Split into sentences using a punctuation lookbehind
  const sentences = actualText.split(/(?<=[.!?])\s+/);
  const matchedSentences: string[] = [];


  for (const sentence of sentences) {
    COMPLIANCE_REGEX.lastIndex = 0;
    if (COMPLIANCE_REGEX.test(sentence)) {
      matchedSentences.push(sentence.trim());
    }
  }

  let body: string;
  if (matchedSentences.length > 0) {
    const displaySentences = matchedSentences.slice(0, 3);
    body = displaySentences.join(" ... ");
    if (matchedSentences.length > 3) {
      body += " ...";
    }
  } else {
    body = actualText.length > 300 ? actualText.substring(0, 300) + "..." : actualText;
  }

  return header ? `${header}${body}` : body;
}

export function AMMReferences() {
  const references = useTerminalStore((s) => s.references);
  const stage = useTerminalStore((s) => s.pipelineStage);
  
  const [activeDocPath, setActiveDocPath] = useState<string | null>(null);
  const [activeSnippet, setActiveSnippet] = useState<string | null>(null);
  const [activeScore, setActiveScore] = useState<number | null>(null);

  const openPdf = (docPath: string, snippet: string, score: number) => {
    setActiveDocPath(docPath);
    setActiveSnippet(snippet);
    setActiveScore(score);
  };

  return (
    <div className="flex flex-col h-full bg-brand-panel border border-brand-border rounded shadow-md overflow-hidden font-mono relative">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-brand-panel-light border-b border-brand-border text-xs uppercase tracking-wider text-brand-text-bright font-bold">
        <div className="flex items-center space-x-2">
          <BookOpen className="h-4 w-4 text-brand-amber" />
          <span>AMM Reference Manual Chunks</span>
        </div>
        <div className="flex items-center space-x-2">
          {stage === "retrieving" && (
            <span className="h-2 w-2 rounded-full bg-brand-amber animate-ping" />
          )}
          <span className="text-[10px] text-brand-text">
            {stage === "retrieving" ? "querying vectors..." : `${references.length} found`}
          </span>
        </div>
      </div>

      {/* References Chunks Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3">
        {references.length > 0 ? (
          references.map((ref, idx) => (
            <div
              key={ref.id || idx}
              className="p-3 bg-brand-canvas border border-brand-border rounded text-left space-y-2 animate-fadeIn"
            >
              {/* Reference Header Metadata */}
              <div className="flex items-center justify-between font-mono text-[10px] text-brand-text-bright border-b border-brand-border/40 pb-1">
                <button
                  onClick={() => openPdf(ref.doc_path, ref.snippet, ref.score)}
                  className="flex items-center space-x-1 hover:text-brand-amber font-mono text-[10px] text-brand-text-bright border-b border-brand-border/40 pb-1 cursor-pointer transition-colors duration-150 select-none text-left truncate max-w-[200px]"
                  title={`Open Sheet: ${ref.doc_path}`}
                >
                  📁 {ref.doc_path}
                </button>
                <span className="text-brand-amber">
                  SCORE: {(ref.score * 100).toFixed(1)}%
                </span>
              </div>
              
              {/* Snippet Block */}
              <p className="text-xs text-brand-text leading-relaxed whitespace-pre-wrap select-text">
                {highlightAmmText(getFocusedSnippet(ref.snippet))}
              </p>
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center h-full py-8 text-center">
            <span className="text-brand-text italic text-xs">
              &gt; No active reference docs loaded.
            </span>
          </div>
        )}
      </div>

      {/* LaTeX-style Paper Modal Viewer Overlay */}
      {activeDocPath && activeSnippet && (
        <div 
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setActiveDocPath(null);
              setActiveSnippet(null);
              setActiveScore(null);
            }
          }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto cursor-pointer"
        >
          <div className="flex flex-col w-full max-w-2xl bg-brand-panel border border-brand-border rounded shadow-2xl p-6 relative max-h-[85vh] my-8 animate-zoomIn cursor-default">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-brand-border pb-3 mb-4">
              <div className="text-left font-mono">
                <h3 className="text-xs uppercase text-brand-text font-bold">AMM Reference Manual Sheet</h3>
                <span className="text-[10px] text-brand-text-bright">{activeDocPath}</span>
              </div>
              <button 
                onClick={() => {
                  setActiveDocPath(null);
                  setActiveSnippet(null);
                  setActiveScore(null);
                }}
                className="px-2.5 py-1 bg-brand-panel-light hover:bg-brand-red text-brand-text hover:text-white rounded border border-brand-border cursor-pointer transition-colors duration-150 font-mono text-[10px]"
              >
                CLOSE [X]
              </button>
            </div>

            {/* LaTeX Paper Sheet (Scroll Wrapper) */}
            <div className="flex-1 overflow-y-auto my-2 pr-1">
              <div className="bg-white text-gray-900 shadow-2xl border border-gray-300 rounded p-8 text-left font-serif text-sm leading-relaxed relative select-text">
                {/* LaTeX Header Decor */}
                <div className="text-center border-b border-gray-200 pb-4 mb-6 font-sans">
                  <h4 className="text-[9px] uppercase tracking-widest text-gray-400 font-bold">
                    Aircraft Maintenance Manual Reference
                  </h4>
                  <h2 className="text-sm font-bold text-gray-800 uppercase mt-1">
                    {activeDocPath.replace(".pdf", "").replace(/_/g, " ")}
                  </h2>
                  {activeScore !== null && (
                    <span className="text-[9px] text-brand-amber font-mono bg-brand-panel px-2 py-0.5 rounded mt-1.5 inline-block">
                      RAG CONFIDENCE: {(activeScore * 100).toFixed(1)}%
                    </span>
                  )}
                </div>

                {/* Justified Text Content with Highlights */}
                <div className="text-justify indent-8 whitespace-pre-line text-gray-800 tracking-wide font-medium">
                  {highlightAmmText(getFocusedSnippet(activeSnippet))}
                </div>
              </div>
            </div>

            {/* Footer Actions */}
            <div className="flex justify-center mt-3 pt-2 border-t border-brand-border/40 shrink-0">
              <a 
                href={`${API_BASE_URL}/api/v1/records/pdf/${activeDocPath}`}
                download
                className="px-4 py-2 bg-brand-panel-light hover:bg-brand-amber text-brand-text-bright hover:text-black rounded border border-brand-border cursor-pointer transition-all duration-150 inline-flex items-center space-x-2 font-mono text-xs uppercase font-bold"
              >
                <span>⬇ Download Full Document</span>
              </a>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
