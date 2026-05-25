import { useEffect, useRef } from "react";
import { useTerminalStore } from "../../../store/terminalStore";
import type { ChecklistSession } from "../../../store/terminalStore";
import type { 
  TranscriptPayload,
  ReferencesPayload,
  ExtractedRecordPayload,
  ValidationResultPayload,
  CompletePayload
} from "../../../types/contracts";

function playNotificationBeep(isSuccess: boolean) {
  try {
    const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new AudioCtxClass();
    
    // Create gain node for low volume (subtle)
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.04, ctx.currentTime); // Low volume (4%)
    gain.connect(ctx.destination);
    
    const now = ctx.currentTime;
    
    if (isSuccess) {
      // Subtle pleasant double chime (C5 -> E5)
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      
      osc1.type = "sine"; // Smooth sine wave
      osc1.frequency.setValueAtTime(523.25, now); // C5
      
      osc2.type = "sine";
      osc2.frequency.setValueAtTime(659.25, now + 0.1); // E5
      
      osc1.connect(gain);
      osc2.connect(gain);
      
      // Control volume envelope to prevent clicking
      gain.gain.setValueAtTime(0.0, now);
      gain.gain.linearRampToValueAtTime(0.04, now + 0.05); // ramp up first note
      gain.gain.setValueAtTime(0.04, now + 0.1);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35); // fade out second note
      
      osc1.start(now);
      osc1.stop(now + 0.15);
      
      osc2.start(now + 0.1);
      osc2.stop(now + 0.35);
    } else {
      // Subtle double low pulse warning (E4 -> D4)
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      
      osc1.type = "triangle"; // Soft triangle wave
      osc1.frequency.setValueAtTime(330.0, now); // E4
      
      osc2.type = "triangle";
      osc2.frequency.setValueAtTime(293.66, now + 0.15); // D4
      
      osc1.connect(gain);
      osc2.connect(gain);
      
      // Volume envelope for warning pulse
      gain.gain.setValueAtTime(0.0, now);
      gain.gain.linearRampToValueAtTime(0.04, now + 0.05);
      gain.gain.setValueAtTime(0.04, now + 0.15);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
      
      osc1.start(now);
      osc1.stop(now + 0.15);
      
      osc2.start(now + 0.15);
      osc2.stop(now + 0.4);
    }
  } catch (error) {
    console.error("Failed to play notification beep:", error);
  }
}

export function stopWarningAudio() {
  // Bypassed: short beeps do not require manual termination
}

export function useSSEStream(connectionId: string | null): void {
  const eventSourceRef = useRef<EventSource | null>(null);

  // Store actions
  const setStage = useTerminalStore((s) => s.setStage);
  const updateTranscript = useTerminalStore((s) => s.updateTranscript);
  const setReferences = useTerminalStore((s) => s.setReferences);
  const setExtractedRecord = useTerminalStore((s) => s.setExtractedRecord);
  const setValidationResult = useTerminalStore((s) => s.setValidationResult);
  const setErrorMessage = useTerminalStore((s) => s.setErrorMessage);
  const addSession = useTerminalStore((s) => s.addSession);

  useEffect(() => {
    if (!connectionId) return;

    // Point to the FastAPI backend SSE endpoint
    const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    const backendUrl = `${API_BASE_URL}/api/v1/records/stream?connection_id=${connectionId}`;
    const es = new EventSource(backendUrl);
    eventSourceRef.current = es;

    es.addEventListener("connection_established", () => {
      setStage("idle");
    });

    es.addEventListener("transcribing", (event) => {
      setStage("transcribing");
      console.log("Pipeline: transcribing status", event.data);
    });

    es.addEventListener("transcript", (event) => {
      try {
        const payload = JSON.parse(event.data) as TranscriptPayload;
        updateTranscript(payload.text);
      } catch (err) {
        console.error("Error parsing transcript event data", err);
      }
    });

    es.addEventListener("retrieving", () => {
      setStage("retrieving");
    });

    es.addEventListener("references", (event) => {
      try {
        const payload = JSON.parse(event.data) as ReferencesPayload;
        setReferences(payload.references);
      } catch (err) {
        console.error("Error parsing references event data", err);
      }
    });

    es.addEventListener("extracting", () => {
      setStage("extracting");
    });

    es.addEventListener("extracted_record", (event) => {
      try {
        const payload = JSON.parse(event.data) as ExtractedRecordPayload;
        setExtractedRecord(payload.record);
      } catch (err) {
        console.error("Error parsing extracted_record event data", err);
      }
    });

    es.addEventListener("validating", () => {
      setStage("validating");
    });

    es.addEventListener("validation_result", (event) => {
      try {
        const payload = JSON.parse(event.data) as ValidationResultPayload;
        setValidationResult(payload.status, payload.details.issues);
        // Play success/failure notification chimes
        playNotificationBeep(payload.status === "PASS");
      } catch (err) {
        console.error("Error parsing validation_result event data", err);
      }
    });

    es.addEventListener("complete", (event) => {
      setStage("completed");
      // Snapshot all pipeline state into a persistent checklist session entry
      try {
        const payload = JSON.parse(event.data) as CompletePayload;
        const storeState = useTerminalStore.getState();
        const session: ChecklistSession = {
          id: payload.record_id || connectionId,
          timestamp: payload.persisted_at || new Date().toISOString(),
          transcript: storeState.transcript,
          record: storeState.extractedRecord,
          validationStatus: storeState.validationStatus === 'PENDING' ? 'FAIL' : storeState.validationStatus,
          validationErrors: storeState.validationErrors,
          references: storeState.references,
        };
        addSession(session);
      } catch (err) {
        console.error("Error archiving session to checklist:", err);
      }
      es.close();
    });

    es.addEventListener("error", (event) => {
      console.error("EventSource connection error:", event);
      // Wait for error payload standard emission
      setErrorMessage("Lost connection stream socket link. Please retry.");
      es.close();
    });

    // Cleanup hook on connection changes or unmounting
    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [
    connectionId,
    setStage,
    updateTranscript,
    setReferences,
    setExtractedRecord,
    setValidationResult,
    setErrorMessage,
    addSession,
  ]);
}
