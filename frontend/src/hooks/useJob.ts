import { useEffect, useState, useRef } from "react";
import { api } from "../api/client";
import type { Job } from "../api/types";

export function useJob(
  jobId: number | null,
  onComplete?: (job: Job) => void
) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (jobId === null) {
      setJob(null);
      setError(null);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async () => {
      try {
        const data = await api.getJob(jobId);
        if (cancelled) return;
        setJob(data);
        if (data.status === "completed") {
          onCompleteRef.current?.(data);
          return;
        }
        if (data.status === "failed") {
          setError(data.error || "Job failed");
          return;
        }
        timer = setTimeout(poll, 2000);
      } catch (err: any) {
        if (cancelled) return;
        setError(err?.message || "Failed to poll job");
      }
    };

    poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  return { job, error, isRunning: job?.status === "queued" || job?.status === "running" };
}
