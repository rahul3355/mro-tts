import { create } from 'zustand';
import type { MaintenanceRecordDTO, ReferenceDocument } from '../types/contracts';

export interface ChecklistSession {
  id: string;                            // connection_id / record_id
  timestamp: string;                     // ISO string
  transcript: string;
  record: MaintenanceRecordDTO | null;
  validationStatus: 'PASS' | 'FAIL';
  validationErrors: string[];
  references: ReferenceDocument[];
}

export type PipelineStage = 
  | 'idle' 
  | 'transcribing' 
  | 'retrieving' 
  | 'extracting' 
  | 'validating' 
  | 'completed' 
  | 'error';

interface TerminalState {
  isRecording: boolean;
  connectionId: string | null;
  pipelineStage: PipelineStage;
  transcript: string;
  references: ReferenceDocument[];
  extractedRecord: MaintenanceRecordDTO | null;
  validationStatus: 'PENDING' | 'PASS' | 'FAIL';
  validationErrors: string[];
  errorMessage: string | null;
  sessions: ChecklistSession[];
  theme: 'light' | 'dark';

  // Setters & Actions
  setIsRecording: (recording: boolean) => void;
  setConnectionId: (id: string | null) => void;
  setStage: (stage: PipelineStage) => void;
  updateTranscript: (text: string) => void;
  setReferences: (refs: ReferenceDocument[]) => void;
  setExtractedRecord: (rec: MaintenanceRecordDTO | null) => void;
  setValidationResult: (status: 'PASS' | 'FAIL', errors: string[]) => void;
  setErrorMessage: (msg: string | null) => void;
  resetTerminal: () => void;
  addSession: (session: ChecklistSession) => void;
  toggleTheme: () => void;
}

export const useTerminalStore = create<TerminalState>((set) => ({
  isRecording: false,
  connectionId: null,
  pipelineStage: 'idle',
  transcript: '',
  references: [],
  extractedRecord: null,
  validationStatus: 'PENDING',
  validationErrors: [],
  errorMessage: null,
  sessions: [],
  theme: 'light',

  setIsRecording: (recording) => set({ isRecording: recording }),
  setConnectionId: (id) => set({ connectionId: id }),
  setStage: (stage) => set({ pipelineStage: stage }),
  updateTranscript: (text) => set({ transcript: text }),
  setReferences: (refs) => set({ references: refs }),
  setExtractedRecord: (rec) => set({ extractedRecord: rec }),
  setValidationResult: (status, errors) => set({ validationStatus: status, validationErrors: errors }),
  setErrorMessage: (msg) => set({ errorMessage: msg, pipelineStage: msg ? 'error' : 'idle' }),

  addSession: (session) => set((state) => ({ sessions: [session, ...state.sessions] })),

  toggleTheme: () => set((state) => {
    const next = state.theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next === 'dark' ? 'dark' : '');
    return { theme: next };
  }),

  resetTerminal: () => set({
    isRecording: false,
    pipelineStage: 'idle',
    transcript: '',
    references: [],
    extractedRecord: null,
    validationStatus: 'PENDING',
    validationErrors: [],
    errorMessage: null
  })
}));
