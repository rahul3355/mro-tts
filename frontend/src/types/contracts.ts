/**
 * API contracts source of truth matching backend Pydantic schemas.
 */

export interface ComplianceParameter {
  label: string;
  value: string;
  spec: string;
  status: "PASS" | "FAIL";
}

export interface MaintenanceRecordDTO {
  part_name: string;
  part_number: string | null;
  ata_chapter: string | null;
  action_performed: string;
  notes: string | null;
  compliance_parameters: ComplianceParameter[];
}

export interface ReferenceDocument {
  id: string;
  doc_path: string;
  score: number;
  snippet: string;
}

export interface ConnectionEstablishedPayload {
  connection_id: string;
  heartbeat_interval_ms: number;
}

export interface TranscribingPayload {
  status: "started" | "completed";
}

export interface TranscriptPayload {
  text: string;
}

export interface RetrievingPayload {
  status: "started" | "completed";
}

export interface ReferencesPayload {
  references: ReferenceDocument[];
}

export interface ExtractingPayload {
  status: "started" | "completed";
}

export interface ExtractedRecordPayload {
  record: MaintenanceRecordDTO;
}

export interface ValidatingPayload {
  status: "started" | "completed";
}

export interface ValidationResultPayload {
  status: "PASS" | "FAIL";
  details: {
    issues: string[];
  };
}

export interface CompletePayload {
  record_id: string;
  persisted_at: string;
}

export interface ErrorPayload {
  stage: "stt" | "rag" | "extraction" | "validation" | "tts" | "db";
  error_code: string;
  message: string;
}
