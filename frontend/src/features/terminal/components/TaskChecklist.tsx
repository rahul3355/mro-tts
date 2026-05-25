import { useState } from "react";
import { useTerminalStore } from "../../../store/terminalStore";
import type { ChecklistSession } from "../../../store/terminalStore";
import { CheckCircle, XCircle, ClipboardList, FileText, Mic } from "lucide-react";

// Expanded regex covering torque, lockwire, resistance, pressure, clearances, and ISO standards
const COMPLIANCE_REGEX = /(\b\d+(?:\.\d+)?\s*(?:to|and|-)\s*\d+(?:\.\d+)?\s*(?:foot-pounds|inch-pounds|ft-lbs|in-lbs|Nm|milliohms|m\u2126|m\u03a9|ohms|\u2126|PSI|bar|inch|inches|in|mm)\b|\b\d+(?:\.\d+)?\s*(?:foot-pounds|inch-pounds|ft-lbs|in-lbs|Nm|milliohms|m\u2126|m\u03a9|ohms|\u2126|PSI|bar|inch|inches|in|mm)\b|safety wire|lockwire|lock-wire|safety-wire|0\.032|ISO\s*\d+|Class\s+[A-Z]|Rmin\s*=\s*\d+.\w+|\bbend radius\b)/gi;

// ─── Helpers ────────────────────────────────────────────────────────────────

function fmtTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-GB", {
      timeZone: "Europe/London",
      year: "2-digit",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }) + " BST";
  } catch {
    return iso;
  }
}

function highlightText(text: string) {
  if (!text) return "";
  const parts = text.split(COMPLIANCE_REGEX);
  return parts.map((part, i) => {
    COMPLIANCE_REGEX.lastIndex = 0;
    if (COMPLIANCE_REGEX.test(part)) {
      return (
        <mark key={i} className="bg-yellow-200 text-gray-900 px-0.5 rounded font-semibold">
          {part}
        </mark>
      );
    }
    return part;
  });
}


// ─── Modal: Transcript ───────────────────────────────────────────────────────

function TranscriptModal({
  session,
  onClose,
}: {
  session: ChecklistSession;
  onClose: () => void;
}) {
  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm cursor-pointer"
    >
      <div className="flex flex-col w-full max-w-2xl bg-brand-panel border border-brand-border rounded shadow-2xl relative animate-zoomIn cursor-default">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-brand-border">
          <div className="font-mono">
            <h3 className="text-xs uppercase text-brand-text font-bold tracking-wider">
              Voice Transcript Log
            </h3>
            <span className="text-[10px] text-brand-text-bright">
              Session · {fmtTimestamp(session.timestamp)}
            </span>
          </div>
          <button
            onClick={onClose}
            className="px-2.5 py-1 bg-brand-panel-light hover:bg-brand-red text-brand-text hover:text-white rounded border border-brand-border cursor-pointer transition-colors duration-150 font-mono text-[10px]"
          >
            CLOSE [X]
          </button>
        </div>

        {/* LaTeX Paper */}
        <div className="p-6 overflow-y-auto max-h-[70vh]">
          <div className="bg-white text-gray-900 shadow-2xl border border-gray-300 rounded p-8 font-serif text-sm leading-relaxed select-text">
            <div className="text-center border-b border-gray-200 pb-4 mb-6 font-sans">
              <h4 className="text-[9px] uppercase tracking-widest text-gray-400 font-bold">
                Technician Voice Record
              </h4>
              <h2 className="text-sm font-bold text-gray-800 uppercase mt-1">
                Operator Spoken Transcript
              </h2>
              <span className="text-[9px] text-gray-500 font-mono mt-1 inline-block">
                {fmtTimestamp(session.timestamp)}
              </span>
            </div>
            <div className="text-justify indent-8 whitespace-pre-line text-gray-800 tracking-wide font-medium leading-8">
              {session.transcript || "No transcript captured."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Modal: Compliance Report ────────────────────────────────────────────────

function ComplianceModal({
  session,
  onClose,
}: {
  session: ChecklistSession;
  onClose: () => void;
}) {
  const rec = session.record;
  const isPass = session.validationStatus === "PASS";

  return (
    <div
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto cursor-pointer"
    >
      <div className="flex flex-col w-full max-w-2xl bg-brand-panel border border-brand-border rounded shadow-2xl relative my-8 animate-zoomIn cursor-default">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-brand-border">
          <div className="font-mono">
            <h3 className="text-xs uppercase text-brand-text font-bold tracking-wider">
              Compliance Report
            </h3>
            <span className="text-[10px] text-brand-text-bright">
              Session · {fmtTimestamp(session.timestamp)}
            </span>
          </div>
          <button
            onClick={onClose}
            className="px-2.5 py-1 bg-brand-panel-light hover:bg-brand-red text-brand-text hover:text-white rounded border border-brand-border cursor-pointer transition-colors duration-150 font-mono text-[10px]"
          >
            CLOSE [X]
          </button>
        </div>

        {/* LaTeX Paper */}
        <div className="p-6 overflow-y-auto max-h-[80vh]">
          <div className="bg-white text-gray-900 shadow-2xl border border-gray-300 rounded p-8 font-serif text-sm leading-relaxed select-text space-y-6">
            {/* Report Title */}
            <div className="text-center border-b border-gray-200 pb-4 font-sans">
              <h4 className="text-[9px] uppercase tracking-widest text-gray-400 font-bold">
                MRO Compliance QA System
              </h4>
              <h2 className="text-sm font-bold text-gray-800 uppercase mt-1">
                Maintenance Compliance Audit Report
              </h2>
              <span className="text-[9px] text-gray-500 font-mono mt-1.5 inline-block">
                {fmtTimestamp(session.timestamp)}
              </span>
            </div>

            {/* Status Badge */}
            <div
              className={`flex items-center justify-center gap-2 py-2.5 rounded border font-bold uppercase tracking-widest text-sm ${
                isPass
                  ? "bg-green-50 border-green-300 text-green-700"
                  : "bg-red-50 border-red-300 text-red-700"
              }`}
            >
              {isPass ? (
                <CheckCircle className="h-5 w-5" />
              ) : (
                <XCircle className="h-5 w-5" />
              )}
              <span>Compliance Status: {isPass ? "VERIFIED - PASS" : "FAILURE - NON-COMPLIANT"}</span>
            </div>

            {/* Extracted Record Section */}
            {rec && (
              <section>
                <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 border-b border-gray-200 pb-1 mb-3 font-sans">
                  § 1 - Structured Maintenance Record
                </h3>
                <table className="w-full text-xs font-sans border-collapse">
                  <tbody>
                    {(() => {
                      const rows = [
                        ["Part / Component", rec.part_name],
                        ["Part Number", rec.part_number ?? "N/A"],
                        ["ATA Chapter", rec.ata_chapter ?? "N/A"],
                        ["Action Performed", rec.action_performed],
                      ];
                      
                      if (rec.compliance_parameters && rec.compliance_parameters.length > 0) {
                        rec.compliance_parameters.forEach((param) => {
                          rows.push([
                            `Metric: ${param.label}`,
                            `${param.value} (Spec: ${param.spec}) - [${param.status}]`
                          ]);
                        });
                      } else {
                        rows.push([
                          "Compliance Metrics",
                          "No metrics extracted for verification."
                        ]);
                      }
                      
                      rows.push(["Notes", rec.notes ?? "N/A"]);
                      
                      return rows.map(([label, value]) => (
                        <tr
                          key={label}
                          className="border-b border-gray-100 last:border-0"
                        >
                          <td className="py-1.5 pr-4 font-semibold text-gray-600 w-40 align-top">
                            {label}
                          </td>
                          <td className="py-1.5 text-gray-800">{value}</td>
                        </tr>
                      ));
                    })()}
                  </tbody>
                </table>
              </section>
            )}

            {/* Compliance Issues */}
            {!isPass && session.validationErrors.length > 0 && (
              <section>
                <h3 className="text-xs font-bold uppercase tracking-widest text-red-600 border-b border-red-200 pb-1 mb-3 font-sans">
                  § 2 - Non-Compliance Issues Identified
                </h3>
                <ul className="list-disc list-inside space-y-1.5 text-xs text-gray-700 font-sans">
                  {session.validationErrors.map((err, i) => (
                    <li key={i} className="marker:text-red-500">
                      {err}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* AMM References Used */}
            {session.references.length > 0 && (
              <section>
                <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 border-b border-gray-200 pb-1 mb-3 font-sans">
                  § 3 - AMM Reference Documents Consulted
                </h3>
                <div className="space-y-3">
                  {session.references.map((ref, i) => (
                    <div
                      key={ref.id || i}
                      className="bg-yellow-50 border border-yellow-200 rounded p-3 font-sans"
                    >
                      <div className="flex justify-between text-[10px] text-gray-500 mb-1.5">
                        <span className="font-semibold text-gray-700">📁 {ref.doc_path}</span>
                        <span>Confidence: {(ref.score * 100).toFixed(1)}%</span>
                      </div>
                      <p className="text-xs text-gray-800 leading-relaxed text-justify">
                        {highlightText(ref.snippet)}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Full Transcript */}
            <section>
              <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 border-b border-gray-200 pb-1 mb-3 font-sans">
                § 4 - Verbatim Technician Transcript
              </h3>
              <p className="text-xs text-gray-700 leading-relaxed indent-8 text-justify whitespace-pre-line">
                {session.transcript || "No transcript captured."}
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function TaskChecklist() {
  const sessions = useTerminalStore((s) => s.sessions);
  const [transcriptModal, setTranscriptModal] = useState<ChecklistSession | null>(null);
  const [complianceModal, setComplianceModal] = useState<ChecklistSession | null>(null);

  if (sessions.length === 0) return null;

  return (
    <>
      {/* ── Section ── */}
      <section className="mt-6">
        <div className="flex items-center space-x-2 border-b border-brand-border pb-3 mb-4">
          <ClipboardList className="h-4 w-4 text-brand-amber" />
          <h2 className="font-mono text-xs uppercase tracking-widest text-brand-text-bright font-bold">
            Task Activity Log - Compliance Checklist
          </h2>
          <span className="text-[10px] text-brand-text font-mono ml-auto">
            {sessions.length} record{sessions.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Table */}
        <div className="bg-brand-panel border border-brand-border rounded shadow-md overflow-hidden font-mono">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-brand-panel-light border-b border-brand-border text-brand-text uppercase tracking-wider text-[10px]">
                <th className="text-left px-4 py-2.5 font-bold w-32">Timestamp</th>
                <th className="text-left px-4 py-2.5 font-bold">Action Log</th>
                <th className="text-left px-4 py-2.5 font-bold w-40">Component Name</th>
                <th className="text-center px-4 py-2.5 font-bold w-28">Status</th>
                <th className="text-center px-4 py-2.5 font-bold w-40">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border/40">
              {sessions.map((session, idx) => {
                const isPass = session.validationStatus === "PASS";
                const actionLog = session.record?.action_performed ?? "Unknown action";
                const componentName = session.record?.part_name ?? "Unknown component";

                return (
                  <tr
                    key={session.id || idx}
                    className="hover:bg-brand-panel-light/50 transition-colors duration-100 animate-fadeIn"
                  >
                    {/* Timestamp */}
                    <td className="px-4 py-3 text-[10px] text-brand-text whitespace-nowrap">
                      {fmtTimestamp(session.timestamp)}
                    </td>

                    {/* Action Log */}
                    <td className="px-4 py-3 text-brand-text-bright leading-relaxed max-w-xs">
                      <span className="block truncate" title={actionLog}>
                        {actionLog}
                      </span>
                    </td>

                    {/* Component Name */}
                    <td className="px-4 py-3">
                      <span
                        className="text-brand-amber font-bold block truncate"
                        title={componentName}
                      >
                        {componentName}
                      </span>
                    </td>

                    {/* Status Badge */}
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          isPass
                            ? "bg-brand-green/10 border-brand-green text-brand-green"
                            : "bg-brand-red/10 border-brand-red text-brand-red animate-pulse"
                        }`}
                      >
                        {isPass ? (
                          <CheckCircle className="h-3 w-3" />
                        ) : (
                          <XCircle className="h-3 w-3" />
                        )}
                        {isPass ? "PASS" : "FAIL"}
                      </span>
                    </td>

                    {/* Action Buttons */}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => setTranscriptModal(session)}
                          title="View Transcript"
                          className="flex items-center gap-1 px-2 py-1 bg-brand-panel-light hover:bg-brand-amber/20 text-brand-text-bright hover:text-brand-amber border border-brand-border rounded transition-colors duration-150 text-[10px] uppercase font-bold"
                        >
                          <Mic className="h-3 w-3" />
                          Transcript
                        </button>
                        <button
                          onClick={() => setComplianceModal(session)}
                          title="View Compliance Report"
                          className={`flex items-center gap-1 px-2 py-1 border rounded transition-colors duration-150 text-[10px] uppercase font-bold ${
                            isPass
                              ? "bg-brand-panel-light hover:bg-brand-green/20 text-brand-text-bright hover:text-brand-green border-brand-border"
                              : "bg-brand-red/5 hover:bg-brand-red/20 text-brand-red border-brand-red/40"
                          }`}
                        >
                          <FileText className="h-3 w-3" />
                          Report
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Modals ── */}
      {transcriptModal && (
        <TranscriptModal
          session={transcriptModal}
          onClose={() => setTranscriptModal(null)}
        />
      )}
      {complianceModal && (
        <ComplianceModal
          session={complianceModal}
          onClose={() => setComplianceModal(null)}
        />
      )}
    </>
  );
}
