import { useState, useCallback } from "react";
import { RecordButton } from "./features/terminal/components/RecordButton";
import { TranscriptView } from "./features/terminal/components/TranscriptView";
import { AMMReferences } from "./features/terminal/components/AMMReferences";
import { ValidationPanel } from "./features/terminal/components/ValidationPanel";
import { TaskChecklist } from "./features/terminal/components/TaskChecklist";
import { useSSEStream, stopWarningAudio } from "./features/terminal/hooks/useSSEStream";
import { useTerminalStore } from "./store/terminalStore";
import { Radio, RefreshCw, AlertTriangle, Sun, Moon } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [sessionConnectionId, setSessionConnectionId] = useState<string | null>(null);

  const connectionId = useTerminalStore((s) => s.connectionId);
  const setStoreConnectionId = useTerminalStore((s) => s.setConnectionId);
  const setStage = useTerminalStore((s) => s.setStage);
  const setErrorMessage = useTerminalStore((s) => s.setErrorMessage);
  const errorMessage = useTerminalStore((s) => s.errorMessage);
  const resetTerminal = useTerminalStore((s) => s.resetTerminal);
  const updateTranscript = useTerminalStore((s) => s.updateTranscript);
  const theme = useTerminalStore((s) => s.theme);
  const toggleTheme = useTerminalStore((s) => s.toggleTheme);

  // Subscribe to SSE stream if connection ID is allocated
  useSSEStream(sessionConnectionId);

  const handleAudioReady = useCallback(async (audioBlob: Blob) => {
    // 1. Generate unique UUID session connection ID
    const newConnectionId = crypto.randomUUID();
    
    // 2. Clear any active warning voice playbacks
    stopWarningAudio();

    // 3. Update states
    resetTerminal();
    setSessionConnectionId(newConnectionId);
    setStoreConnectionId(newConnectionId);
    setStage("transcribing");

    // 4. Send request payload via Form Data multipart
    const formData = new FormData();
    formData.append("audio", audioBlob, "maintenance_log.webm");
    formData.append("connection_id", newConnectionId);

    try {
      console.log(`Submitting voice log upload with session token: ${newConnectionId}`);
      const response = await fetch(`${API_BASE_URL}/api/v1/records/process`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Server failed to register upload payload");
      }
      
      console.log("Audio file registered successfully. Listening to progress events...");
    } catch (err: unknown) {
      console.error("Failed to process audio feed:", err);
      const message = err instanceof Error ? err.message : "Failed to establish upload. Please verify backend is running.";
      setErrorMessage(message);
      setSessionConnectionId(null);
    }
  }, [resetTerminal, setStoreConnectionId, setStage, setErrorMessage]);

  const handleTextProcess = useCallback(async (newText: string) => {
    // 1. Generate unique UUID session connection ID
    const newConnectionId = crypto.randomUUID();
    
    // 2. Clear any active warning voice playbacks
    stopWarningAudio();

    // 3. Update states
    resetTerminal();
    updateTranscript(newText);
    setSessionConnectionId(newConnectionId);
    setStoreConnectionId(newConnectionId);
    setStage("retrieving");

    // 4. Send request payload via Form Data multipart
    const formData = new FormData();
    formData.append("text", newText);
    formData.append("connection_id", newConnectionId);

    try {
      console.log(`Submitting edited text log upload with session token: ${newConnectionId}`);
      const response = await fetch(`${API_BASE_URL}/api/v1/records/process-text`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Server failed to register text processing payload");
      }
      
      console.log("Text registered successfully. Listening to progress events...");
    } catch (err: unknown) {
      console.error("Failed to process text feed:", err);
      const message = err instanceof Error ? err.message : "Failed to establish text processing connection. Please verify backend is running.";
      setErrorMessage(message);
      setSessionConnectionId(null);
    }
  }, [resetTerminal, updateTranscript, setStoreConnectionId, setStage, setErrorMessage]);

  const handleReset = () => {
    stopWarningAudio();
    resetTerminal();
    setSessionConnectionId(null);
    setStoreConnectionId(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-brand-canvas text-brand-text font-sans p-4 md:p-6 select-none">
      {/* Top Banner Status Bar */}
      <header className="flex flex-col md:flex-row items-center justify-between border-b border-brand-border pb-4 mb-6 space-y-3 md:space-y-0">
        <div className="flex items-center space-x-3 text-left">
          <div className="h-3 w-3 rounded-full bg-brand-amber animate-pulse border border-brand-amber/40" />
          <div>
            <h1 className="text-lg font-mono font-bold tracking-widest text-brand-text-bright uppercase">
              mro-tts // MAINTENANCE CONSOLE
            </h1>
            <p className="text-[10px] font-mono text-brand-text tracking-wider uppercase">
              Operational compliance verification terminal
            </p>
          </div>
        </div>

        {/* Live Network Indicators */}
        <div className="flex items-center space-x-4 font-mono text-[10px]">
          {connectionId && (
            <div className="bg-brand-panel px-3 py-1 rounded border border-brand-border flex items-center space-x-1.5 text-brand-text-bright">
              <span className="text-brand-text">SESSION ID:</span>
              <span className="truncate max-w-[120px] font-bold" title={connectionId}>
                {connectionId}
              </span>
            </div>
          )}
          <div className="flex items-center space-x-1.5 bg-brand-panel px-3 py-1 rounded border border-brand-border text-brand-green">
            <Radio className="h-3.5 w-3.5 animate-pulse" />
            <span className="font-bold">SYSTEM ACTIVE</span>
          </div>
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="flex items-center space-x-1 hover:text-brand-amber bg-brand-panel-light hover:bg-brand-panel px-3 py-1 rounded border border-brand-border transition-colors duration-150"
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {theme === 'dark' ? (
              <Sun className="h-3.5 w-3.5" />
            ) : (
              <Moon className="h-3.5 w-3.5" />
            )}
            <span>{theme === 'dark' ? 'LIGHT' : 'DARK'}</span>
          </button>

          <button
            onClick={handleReset}
            className="flex items-center space-x-1 hover:text-brand-amber bg-brand-panel-light hover:bg-brand-panel px-3 py-1 rounded border border-brand-border transition-colors duration-150"
            title="Reset Terminal Console"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>RESET</span>
          </button>
        </div>
      </header>

      {/* Main Terminal Workspace Layout */}
      <main className="flex-grow grid grid-cols-1 lg:grid-cols-12 gap-6 lg:h-[600px] lg:min-h-[500px] min-h-0">
        {/* Left Control Column (Record and Transcript) */}
        <section className="lg:col-span-5 flex flex-col space-y-6 lg:h-full min-h-0">
          <div className="bg-brand-panel border border-brand-border rounded p-6 shadow-md text-center shrink-0">
            <h2 className="font-mono text-xs uppercase tracking-widest text-brand-text-bright border-b border-brand-border/40 pb-2 mb-4 font-bold">
              LOG RECORD TRIGGER
            </h2>
            <RecordButton onAudioReady={handleAudioReady} />
          </div>

          <div className="flex-grow flex flex-col min-h-0">
            <TranscriptView onTextProcess={handleTextProcess} />
          </div>
        </section>

        {/* Right Intel Column (References and Compliances) */}
        <section className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-6 lg:h-full min-h-0">
          <div className="lg:h-full min-h-0 flex flex-col">
            <AMMReferences />
          </div>
          <div className="lg:h-full min-h-0 flex flex-col">
            <ValidationPanel />
          </div>
        </section>
      </main>

      {/* Task Activity Log - Compliance Checklist */}
      <TaskChecklist />

      {/* Global Error Telemetry Banner */}
      {errorMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center space-x-3 bg-brand-red/90 border-2 border-brand-red text-white p-4 rounded shadow-2xl animate-slideIn max-w-sm font-mono text-xs text-left">
          <AlertTriangle className="h-5 w-5 shrink-0 animate-bounce" />
          <div>
            <span className="font-bold block uppercase tracking-wider mb-0.5">Hardware / Socket Link Error</span>
            <p className="text-white/80">{errorMessage}</p>
          </div>
        </div>
      )}
    </div>
  );
}
