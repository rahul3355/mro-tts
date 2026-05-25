import { useTerminalStore } from "../../../store/terminalStore";
import { ShieldCheck, ShieldAlert, XCircle } from "lucide-react";

export function ValidationPanel() {
  const record = useTerminalStore((s) => s.extractedRecord);
  const status = useTerminalStore((s) => s.validationStatus);
  const errors = useTerminalStore((s) => s.validationErrors);
  const stage = useTerminalStore((s) => s.pipelineStage);

  const getStatusColor = () => {
    if (status === "PASS") return "text-brand-green border-brand-green bg-brand-green/10";
    if (status === "FAIL") return "text-brand-red border-brand-red bg-brand-red/10 animate-pulse";
    return "text-brand-text border-brand-border bg-brand-panel-light";
  };

  return (
    <div className="flex flex-col h-full bg-brand-panel border border-brand-border rounded shadow-md overflow-hidden font-mono">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-brand-panel-light border-b border-brand-border text-xs uppercase tracking-wider text-brand-text-bright font-bold">
        <div className="flex items-center space-x-2">
          {status === "FAIL" ? (
            <ShieldAlert className="h-4 w-4 text-brand-red animate-pulse" />
          ) : (
            <ShieldCheck className="h-4 w-4 text-brand-amber" />
          )}
          <span>Compliance Validation Report</span>
        </div>
        <span className="text-[10px] text-brand-text">
          {(stage === "extracting" || stage === "validating")
            ? "generating report..."
            : stage === "completed" || status !== "PENDING"
            ? "complete"
            : "standby"}
        </span>
      </div>

      {/* Infinite Progress Bar - visible while report is being generated */}
      {(stage === "extracting" || stage === "validating") && (
        <div className="relative w-full h-1 bg-brand-border overflow-hidden">
          <div className="progress-sweep absolute inset-y-0 w-2/5 bg-brand-amber rounded-full" />
        </div>
      )}

      {/* Main Panel Content */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
        {/* Status Indicator OR Generating Banner */}
        {(stage === "extracting" || stage === "validating") ? (
          <div className="flex flex-col items-center justify-center gap-2 py-3 px-4 rounded border border-brand-amber/30 bg-brand-amber/5 text-center animate-fadeIn">
            <div className="flex items-center gap-2 text-brand-amber font-bold text-[11px] uppercase tracking-widest">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-amber animate-ping inline-block" />
              Generating Compliance Report
            </div>
            <p className="text-[10px] text-brand-text leading-relaxed">
              Analysing transcript against AMM reference chunks&hellip;
            </p>
          </div>
        ) : (
          <div className={`flex items-center justify-center py-2 px-4 rounded border text-center font-bold uppercase tracking-widest ${getStatusColor()}`}>
            {status === "PASS" && (
              <div className="flex items-center space-x-2 text-sm">
                <span>COMPLIANCE STATUS: VERIFIED</span>
              </div>
            )}
            {status === "FAIL" && (
              <div className="flex items-center space-x-2 text-sm">
                <XCircle className="h-4 w-4 fill-current" />
                <span>COMPLIANCE STATUS: FAILURE</span>
              </div>
            )}
            {status === "PENDING" && <span>AWAITING LOG PROCESSING...</span>}
          </div>
        )}

        {/* Structured QA Data Section */}
        {record ? (
          <div className="space-y-3 bg-brand-canvas border border-brand-border p-3 rounded text-left">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-brand-text block text-[9px] uppercase tracking-wider">ATA Chapter</span>
                <span className="text-brand-text-bright font-bold text-xs">{record.ata_chapter || "N/A"}</span>
              </div>
              <div>
                <span className="text-brand-text block text-[9px] uppercase tracking-wider">Component Name</span>
                <span className="text-brand-text-bright font-bold text-xs truncate block" title={record.part_name}>
                  {record.part_name}
                </span>
              </div>
              <div className="col-span-2 border-t border-brand-border/40 my-0.5"></div>
              <div className="col-span-2">
                <span className="text-brand-text block text-[9px] uppercase tracking-wider">Action Log</span>
                <span className="text-brand-text-bright text-xs block truncate" title={record.action_performed}>
                  {record.action_performed}
                </span>
              </div>
            </div>

            {/* Check if compliance_parameters is available */}
            {record.compliance_parameters && record.compliance_parameters.length > 0 ? (
              <div className="mt-2">
                <span className="text-brand-text block text-[9px] uppercase tracking-wider mb-1.5 border-b border-brand-border/40 pb-0.5">
                  Compliance Metrics Check
                </span>
                <div className="overflow-x-auto">
                  <table className="w-full text-[10px] font-mono border-collapse">
                    <thead>
                      <tr className="text-brand-text uppercase tracking-wider text-[8px] border-b border-brand-border/40">
                        <th className="text-left pb-1">Parameter</th>
                        <th className="text-left pb-1 px-2">Logged</th>
                        <th className="text-left pb-1 px-2">Spec Limit</th>
                        <th className="text-center pb-1">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-border/20">
                      {record.compliance_parameters.map((param, index) => (
                        <tr key={index} className="hover:bg-brand-panel-light/30">
                          <td className="py-1 font-bold text-brand-text-bright truncate max-w-[90px]" title={param.label}>
                            {param.label}
                          </td>
                          <td className="py-1 px-2 text-brand-text-bright">{param.value}</td>
                          <td className="py-1 px-2 text-brand-text truncate max-w-[80px]" title={param.spec}>{param.spec}</td>
                          <td className="py-1 text-center font-bold">
                            <span className={param.status === "PASS" ? "text-brand-green" : "text-brand-red animate-pulse"}>
                              {param.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="py-2 text-center italic text-brand-text text-[10px]">
                &gt; No compliance metrics were extracted to verify.
              </div>
            )}
          </div>
        ) : (
          <div className="py-6 text-center italic text-brand-text text-xs">
            &gt; Waiting for compliance dataset parameters.
          </div>
        )}

        {/* Validation Issues Log */}
        {status === "FAIL" && errors.length > 0 && (
          <div className="p-3 bg-brand-red/5 border border-brand-red/30 rounded text-left">
            <span className="text-brand-red block font-bold text-[9px] uppercase tracking-wider border-b border-brand-red/20 pb-1 mb-2">
              Compliance Issue Reports
            </span>
            <ul className="space-y-1.5 text-[10px] leading-relaxed text-brand-text-bright list-disc list-inside">
              {errors.map((err, idx) => (
                <li key={idx} className="marker:text-brand-red">
                  {err}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
