import { useState, useRef, useCallback } from "react";
import { useTerminalStore } from "../../../store/terminalStore";

export function useAudioRecorder() {
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  
  const isRecording = useTerminalStore((s) => s.isRecording);
  const setIsRecording = useTerminalStore((s) => s.setIsRecording);
  const setErrorMessage = useTerminalStore((s) => s.setErrorMessage);

  const startRecording = useCallback(async () => {
    audioChunksRef.current = [];
    setAudioBlob(null);
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      
      streamRef.current = stream;

      const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioContext = new AudioCtxClass({
        sampleRate: 16000,
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      // bufferSize 4096, 1 input channel, 1 output channel
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        // We must copy the Float32Array data since inputBuffer is reused
        audioChunksRef.current.push(new Float32Array(inputData));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
      setErrorMessage(null);
    } catch (error: unknown) {
      console.error("Microphone hardware access denied:", error);
      const message = error instanceof Error ? error.message : "Failed to access microphone. Please check system permissions.";
      setErrorMessage(message);
      setIsRecording(false);
    }
  }, [setIsRecording, setErrorMessage]);

  const stopRecording = useCallback(() => {
    if (!isRecording) return;

    setIsRecording(false);

    // Disconnect and close Web Audio API graph
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch((err) => console.error("Error closing AudioContext:", err));
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Flatten chunks to a single Float32Array buffer
    const chunks = audioChunksRef.current;
    const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const flattened = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      flattened.set(chunk, offset);
      offset += chunk.length;
    }

    // Encode to 16kHz mono WAV Blob
    const wavBlob = bufferToWav(flattened, 16000);
    setAudioBlob(wavBlob);
  }, [isRecording, setIsRecording]);

  return {
    isRecording,
    audioBlob,
    startRecording,
    stopRecording,
  };
}

// WAV Encoder helper functions
function bufferToWav(buffer: Float32Array, sampleRate: number): Blob {
  const bufferLength = buffer.length;
  const wavBuffer = new ArrayBuffer(44 + bufferLength * 2);
  const view = new DataView(wavBuffer);

  /* RIFF identifier */
  writeString(view, 0, "RIFF");
  /* file length */
  view.setUint32(4, 36 + bufferLength * 2, true);
  /* RIFF type */
  writeString(view, 8, "WAVE");
  /* format chunk identifier */
  writeString(view, 12, "fmt ");
  /* format chunk length */
  view.setUint32(16, 16, true);
  /* sample format (raw PCM = 1) */
  view.setUint16(20, 1, true);
  /* channel count */
  view.setUint16(22, 1, true);
  /* sample rate */
  view.setUint32(24, sampleRate, true);
  /* byte rate (sample rate * block align) */
  view.setUint32(28, sampleRate * 2, true);
  /* block align (channel count * bytes per sample) */
  view.setUint16(32, 2, true);
  /* bits per sample */
  view.setUint16(34, 16, true);
  /* data chunk identifier */
  writeString(view, 36, "data");
  /* data chunk length */
  view.setUint32(40, bufferLength * 2, true);

  // Write PCM audio samples
  floatTo16BitPCM(view, 44, buffer);

  return new Blob([view], { type: "audio/wav" });
}

function floatTo16BitPCM(output: DataView, offset: number, input: Float32Array) {
  for (let i = 0; i < input.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}
