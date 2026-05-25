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
  const pollIntervalRef = useRef<any>(null);

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

    const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
    let isPolling = false;
    let processedEventCount = 0;

    const startPollingFallback = (connId: string) => {
      if (isPolling || pollIntervalRef.current) return;
      isPolling = true;
      console.warn(`EventSource failed or was blocked. Falling back to HTTP polling for connection ID: ${connId}`);

      pollIntervalRef.current = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/api/v1/records/status?connection_id=${connId}`);
          if (!response.ok) {
            throw new Error(`Failed to fetch status: ${response.statusText}`);
          }
          const events = await response.json() as Array<{ event: string; data: any }>;

          // Process any new events in the history array
          for (let i = processedEventCount; i < events.length; i++) {
            const { event: eventName, data } = events[i];
            console.log(`Polling Fallback [${i}]: Processing event '${eventName}'`, data);

            switch (eventName) {
              case "transcribing":
                setStage("transcribing");
                break;
              case "transcript":
                updateTranscript(data.text);
                break;
              case "retrieving":
                setStage("retrieving");
                break;
              case "references":
                setReferences(data.references);
                break;
              case "extracting":
                setStage("extracting");
                break;
              case "extracted_record":
                setExtractedRecord(data.record);
                break;
              case "validating":
                setStage("validating");
                break;
              case "validation_result":
                setValidationResult(data.status, data.details.issues);
                playNotificationBeep(data.status === "PASS");
                break;
              case "complete":
                setStage("completed");
                try {
                  const storeState = useTerminalStore.getState();
                  const session: ChecklistSession = {
                    id: data.record_id || connId,
                    timestamp: data.persisted_at || new Date().toISOString(),
                    transcript: storeState.transcript,
                    record: storeState.extractedRecord,
                    validationStatus: storeState.validationStatus === 'PENDING' ? 'FAIL' : storeState.validationStatus,
                    validationErrors: storeState.validationErrors,
                    references: storeState.references,
                  };
                  addSession(session);
                } catch (err) {
                  console.error("Error archiving session via polling:", err);
                }
                stopPolling();
                break;
              case "error":
                setErrorMessage(data.message || "An error occurred during verification.");
                stopPolling();
                break;
              default:
                break;
            }
            processedEventCount++;
          }
        } catch (err) {
          console.error("Error during polling fallback:", err);
        }
      }, 1500);
    };

    const stopPolling = () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      isPolling = false;
    };

    // Point to the FastAPI backend SSE endpoint
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
        playNotificationBeep(payload.status === "PASS");
      } catch (err) {
        console.error("Error parsing validation_result event data", err);
      }
    });

    es.addEventListener("complete", (event) => {
      setStage("completed");
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
      console.warn("EventSource connection error, falling back to HTTP polling...", event);
      es.close();
      startPollingFallback(connectionId);
    });

    // Cleanup hook on connection changes or unmounting
    return () => {
      es.close();
      eventSourceRef.current = null;
      stopPolling();
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
