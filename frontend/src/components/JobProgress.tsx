import React from "react";
import { CheckCircle2, AlertTriangle, Loader2, Terminal } from "lucide-react";
import type { Job } from "../api/types";

interface JobProgressProps {
  job: Job | null;
  error?: string | null;
  title?: string;
  onDismiss?: () => void;
}

export const JobProgress: React.FC<JobProgressProps> = ({
  job,
  error,
  title,
  onDismiss,
}) => {
  if (!job && !error) return null;

  const pct = Math.round(((job?.progress ?? 0) * 100));
  const status = job?.status || (error ? "failed" : "queued");

  const logLines: string[] = React.useMemo(() => {
    if (!job?.log) return [];
    if (Array.isArray(job.log)) return job.log.slice(-8);
    return String(job.log)
      .split(/\r?\n/)
      .filter(Boolean)
      .slice(-8);
  }, [job?.log]);

  return (
    <div className="bg-ink-900 border border-white/10 rounded-md p-3 text-xs space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-medium text-slate-200">
          {status === "running" || status === "queued" ? (
            <Loader2 className="w-4 h-4 text-glacier-400 animate-spin shrink-0" />
          ) : status === "completed" ? (
            <CheckCircle2 className="w-4 h-4 text-hazard-low shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-hazard-veryhigh shrink-0" />
          )}
          <span>
            {title || (job ? `Job #${job.id} (${job.job_type})` : "Processing Job")}
          </span>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider font-mono ${
              status === "completed"
                ? "bg-hazard-low/15 text-hazard-low border border-hazard-low/30"
                : status === "failed"
                ? "bg-hazard-veryhigh/15 text-hazard-veryhigh border border-hazard-veryhigh/30"
                : "bg-glacier-400/15 text-glacier-300 border border-glacier-400/30"
            }`}
          >
            {status}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-slate-400">{pct}%</span>
          {onDismiss && (status === "completed" || status === "failed") && (
            <button
              onClick={onDismiss}
              className="text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>

      <div className="w-full h-1.5 bg-ink-950 rounded-full overflow-hidden border border-white/5">
        <div
          className={`h-full transition-all duration-300 ${
            status === "failed"
              ? "bg-hazard-veryhigh"
              : status === "completed"
              ? "bg-hazard-low"
              : "bg-glacier-400"
          }`}
          style={{ width: `${Math.max(4, Math.min(100, pct))}%` }}
        />
      </div>

      {logLines.length > 0 && (
        <div className="bg-ink-950/90 border border-white/5 rounded p-2 font-mono text-[11px] text-slate-400 max-h-32 overflow-y-auto space-y-0.5">
          <div className="flex items-center gap-1 text-[10px] text-slate-500 mb-1">
            <Terminal className="w-3 h-3" />
            <span>Live Log Tail</span>
          </div>
          {logLines.map((line, i) => (
            <div key={i} className="truncate">
              {line}
            </div>
          ))}
        </div>
      )}

      {(error || job?.error) && (
        <div className="text-hazard-veryhigh bg-hazard-veryhigh/10 border border-hazard-veryhigh/20 rounded p-2 font-mono text-[11px]">
          {error || job?.error}
        </div>
      )}
    </div>
  );
};
