import { useState, useEffect } from "react";
import { useTerminalStore } from "../../../store/terminalStore";
import { Terminal, Edit2 } from "lucide-react";

interface TranscriptViewProps {
  onTextProcess?: (text: string) => void;
}

export function TranscriptView({ onTextProcess }: TranscriptViewProps) {
  const transcript = useTerminalStore((s) => s.transcript);
  const stage = useTerminalStore((s) => s.pipelineStage);

  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");

  // Sync state with store transcript when it updates from outside
  useEffect(() => {
    setEditedText(transcript || "");
    setIsEditing(false);
  }, [transcript]);

  const handleEditToggle = () => {
    if (stage === "transcribing") return;
    setIsEditing((prev) => !prev);
    if (isEditing) {
      // Revert if closing edit mode
      setEditedText(transcript || "");
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedText(transcript || "");
  };

  const handleInsert = () => {
    if (editedText.trim() && editedText.trim() !== transcript) {
      onTextProcess?.(editedText.trim());
    }
  };

  return (
    <div className="flex flex-col h-full bg-brand-panel border border-brand-border rounded shadow-md overflow-hidden font-mono">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-brand-panel-light border-b border-brand-border text-xs uppercase tracking-wider text-brand-text-bright font-bold">
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-brand-amber" />
          <span>Operator Voice Stream Console</span>
        </div>
        <div className="flex items-center space-x-3">
          {/* Edit icon appears in the red highlighted area when transcript is present and not currently transcribing */}
          {transcript && stage !== "transcribing" && (
            <button
              onClick={handleEditToggle}
              className={`text-brand-text hover:text-brand-amber transition-colors p-1 rounded hover:bg-brand-panel transition-all cursor-pointer ${
                isEditing ? "text-brand-amber bg-brand-panel" : ""
              }`}
              title="Edit Transcript"
            >
              <Edit2 className="h-3.5 w-3.5" />
            </button>
          )}
          <div className="flex items-center space-x-2">
            {stage === "transcribing" && (
              <span className="h-2 w-2 rounded-full bg-brand-amber animate-ping" />
            )}
            <span className="text-[10px] text-brand-text">
              {stage === "transcribing" ? "transcribing..." : "connected"}
            </span>
          </div>
        </div>
      </div>

      {/* Terminal Body */}
      <div className="flex-1 p-4 overflow-y-auto text-sm leading-relaxed text-left flex flex-col justify-between">
        <div className="flex-1">
          {isEditing ? (
            <textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              className="w-full h-full min-h-[140px] bg-brand-panel-light text-brand-text-bright border border-brand-border rounded p-3 font-mono text-sm focus:outline-none focus:border-brand-amber resize-none"
              placeholder="Edit transcript text here..."
              autoFocus
            />
          ) : transcript ? (
            <p className="text-brand-text-bright border-l-2 border-brand-green pl-3 animate-fadeIn">
              {transcript}
            </p>
          ) : (
            <p className="text-brand-text italic text-xs select-none">
              &gt; Waiting for audio feed input connection...
            </p>
          )}
        </div>

        {/* Insert Button Area (Blue highlighted area in screenshot) */}
        {isEditing && (
          <div className="mt-4 flex justify-end space-x-2 animate-fadeIn border-t border-brand-border/40 pt-3 shrink-0">
            <button
              onClick={handleCancel}
              className="flex items-center space-x-1 hover:text-brand-text-bright bg-brand-panel-light hover:bg-brand-panel px-3 py-1.5 rounded border border-brand-border text-xs font-mono transition-colors cursor-pointer"
            >
              Cancel
            </button>
            {editedText.trim() !== transcript && (
              <button
                onClick={handleInsert}
                className="flex items-center space-x-1 bg-brand-amber hover:bg-brand-amber-hover text-white px-4 py-1.5 rounded border border-brand-amber/40 hover:border-brand-amber text-xs font-mono font-bold uppercase tracking-wider shadow transition-all cursor-pointer"
              >
                Insert
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
