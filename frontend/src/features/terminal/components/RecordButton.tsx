import { motion } from "framer-motion";
import { Mic, Square } from "lucide-react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import { useEffect } from "react";

interface RecordButtonProps {
  onAudioReady: (blob: Blob) => void;
}

export function RecordButton({ onAudioReady }: RecordButtonProps) {
  const { isRecording, audioBlob, startRecording, stopRecording } = useAudioRecorder();

  // Forward audio blob back to the parent once recorded
  useEffect(() => {
    if (audioBlob) {
      onAudioReady(audioBlob);
    }
  }, [audioBlob, onAudioReady]);

  const handlePress = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center space-y-4 py-8">
      <div className="relative">
        {/* Outer Pulsating Rings when active */}
        {isRecording && (
          <>
            <motion.div
              className="absolute inset-0 rounded-full bg-brand-red/20"
              animate={{ scale: [1, 1.8, 1], opacity: [0.6, 0, 0.6] }}
              transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
            />
            <motion.div
              className="absolute inset-0 rounded-full bg-brand-red/10"
              animate={{ scale: [1, 2.4, 1], opacity: [0.4, 0, 0.4] }}
              transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut", delay: 0.5 }}
            />
          </>
        )}

        {/* Central Core Button */}
        <motion.button
          onClick={handlePress}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          aria-label={isRecording ? "Stop Recording" : "Start Recording"}
          className={`relative z-10 flex h-28 w-28 items-center justify-center rounded-full border-4 shadow-lg focus:outline-none transition-colors duration-300 ${
            isRecording
              ? "bg-brand-canvas border-brand-red text-brand-red"
              : "bg-brand-panel-light border-brand-border text-brand-amber hover:text-brand-amber-hover hover:border-brand-amber"
          }`}
        >
          {isRecording ? (
            <Square className="h-10 w-10 fill-current animate-pulse" />
          ) : (
            <Mic className="h-12 w-12" />
          )}
        </motion.button>
      </div>

      {/* Telemetry Status Labels */}
      <div className="text-center font-mono text-xs tracking-wider uppercase">
        {isRecording ? (
          <span className="text-brand-red animate-pulse font-bold">
            [ REC ] LIVE CAPTURE ACTIVE...
          </span>
        ) : (
          <span className="text-brand-text">
            READY TO LOG - CLICK MIC TO START
          </span>
        )}
      </div>

      {/* Sample phrase hint - always visible */}
      <p className="text-center font-sans text-[11px] text-brand-text italic normal-case max-w-[260px] leading-relaxed px-2">
        Try speaking: &ldquo;Composite cure vacuum bagging maintained at 24 inches of mercury and positive curing pressure at 85 psi.&rdquo;
      </p>
    </div>
  );
}
