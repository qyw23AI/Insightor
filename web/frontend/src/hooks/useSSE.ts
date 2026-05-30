/* Multi-job SSE hook for real-time analysis progress */

import { useEffect, useRef, useState } from 'react';
import type { Finding } from '../types/urf';

export interface JobProgress {
  jobId: string;
  prUrl: string;
  prNumber: number;
  repo: string;
  step: string;
  stepIndex: number;
  stepTotal: number;
  findings: Finding[];
  status: 'pending' | 'running' | 'done' | 'error';
  error: string | null;
  resultSummary: DoneData | null;
  startTime: number | null;
}

interface DoneData {
  meta: Record<string, unknown>;
  stats: Record<string, unknown>;
  findings_count: number;
  merge_readiness: Record<string, unknown> | null;
  diff_text: string;
}

interface JobMeta {
  job_id: string;
  pr_url: string;
  pr_number: number;
  repo?: string;
  tool?: string;
  depth?: string;
  status?: string;
  error?: string | null;
}

/** Max time a job can stay "pending" (no SSE events received) before being marked error. */
const PENDING_TIMEOUT_MS = 30_000;
/** Max retry errors before giving up on a CONNECTING EventSource. */
const MAX_ERROR_COUNT = 5;

export function useMultiSSE(jobMetas: JobMeta[]) {
  const [jobs, setJobs] = useState<Record<string, JobProgress>>({});
  const [overallProgress, setOverallProgress] = useState(0);
  const [overallDone, setOverallDone] = useState(false);

  // Track error counts & pending timeouts per job (not in state — no re-render needed)
  const errorCountRef = useRef<Record<string, number>>({});
  const pendingTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  // --- Build a stable key from job IDs to use as effect dependency ---
  const jobIdsKey = jobMetas.map(j => j.job_id).sort().join(',');

  // --- Initialize / reset jobs state ---
  useEffect(() => {
    // Cleanup: clear all jobs when runningJobs becomes empty
    if (jobMetas.length === 0) {
      setJobs({});
      setOverallDone(false);
      setOverallProgress(0);
      errorCountRef.current = {};
      return;
    }

    setJobs(prev => {
      const next = { ...prev };
      for (const j of jobMetas) {
        if (!next[j.job_id]) {
          next[j.job_id] = {
            jobId: j.job_id,
            prUrl: j.pr_url,
            prNumber: j.pr_number,
            repo: j.repo || '',
            step: 'Queued...',
            stepIndex: 0,
            stepTotal: 8,
            findings: [],
            status: 'pending',
            error: null,
            resultSummary: null,
            startTime: Date.now(),  // track init time for timeout detection
          };
          // Reset error count for new jobs
          errorCountRef.current[j.job_id] = 0;
        }
      }
      return next;
    });
    setOverallDone(false);
    setOverallProgress(0);
  }, [jobIdsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Timeout: mark pending jobs as error after PENDING_TIMEOUT_MS ---
  useEffect(() => {
    // Clear old timers
    for (const [jid, timer] of Object.entries(pendingTimersRef.current)) {
      clearTimeout(timer);
      delete pendingTimersRef.current[jid];
    }

    for (const j of jobMetas) {
      const jid = j.job_id;
      // Only set timer for jobs currently in 'pending' state
      pendingTimersRef.current[jid] = setTimeout(() => {
        setJobs(prev => {
          const cur = prev[jid];
          if (cur && cur.status === 'pending') {
            return {
              ...prev,
              [jid]: { ...cur, status: 'error' as const, error: 'Timed out waiting for job to start' },
            };
          }
          return prev;
        });
        delete pendingTimersRef.current[jid];
      }, PENDING_TIMEOUT_MS);
    }

    return () => {
      for (const timer of Object.values(pendingTimersRef.current)) {
        clearTimeout(timer);
      }
    };
  }, [jobIdsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Connect SSE to each job ---
  useEffect(() => {
    const sources: EventSource[] = [];

    for (const job of jobMetas) {
      const jid = job.job_id;

      // Skip jobs already done or errored (but read latest state via functional setJobs)
      // We always open connections for non-done/non-error jobs.
      // Use a ref-based check to avoid stale closure over `jobs`.
      const skip = jobs[jid]?.status === 'done' || jobs[jid]?.status === 'error';
      if (skip) continue;

      const url = `/api/analyze/${jid}/stream`;
      const es = new EventSource(url);
      sources.push(es);
      errorCountRef.current[jid] = errorCountRef.current[jid] || 0;

      es.addEventListener('step', (e) => {
        try {
          const data = JSON.parse(e.data);
          setJobs(prev => ({
            ...prev,
            [jid]: {
              ...prev[jid],
              step: data.step || prev[jid]?.step || '',
              stepIndex: data.step_index || 0,
              stepTotal: data.step_total || 8,
              status: 'running' as const,
              startTime: prev[jid]?.startTime || Date.now(),
            },
          }));
          // Clear timeout on first step — job is alive
          if (pendingTimersRef.current[jid]) {
            clearTimeout(pendingTimersRef.current[jid]);
            delete pendingTimersRef.current[jid];
          }
          errorCountRef.current[jid] = 0; // reset on successful event
        } catch { /* ignore */ }
      });

      es.addEventListener('finding', (e) => {
        try {
          const f = JSON.parse(e.data) as Finding;
          setJobs(prev => ({
            ...prev,
            [jid]: {
              ...prev[jid],
              findings: [...(prev[jid]?.findings || []), f],
            },
          }));
        } catch { /* ignore */ }
      });

      es.addEventListener('done', (e) => {
        try {
          const data = JSON.parse(e.data) as DoneData;
          setJobs(prev => ({
            ...prev,
            [jid]: {
              ...prev[jid],
              status: 'done' as const,
              step: 'Complete',
              stepIndex: 8,
              resultSummary: data,
            },
          }));
          // Clear timeout
          if (pendingTimersRef.current[jid]) {
            clearTimeout(pendingTimersRef.current[jid]);
            delete pendingTimersRef.current[jid];
          }
          es.close();
        } catch { /* ignore */ }
      });

      // Custom "fail" event from backend (job-level error)
      es.addEventListener('fail', (e) => {
        try {
          const data = JSON.parse(e.data);
          setJobs(prev => ({
            ...prev,
            [jid]: {
              ...prev[jid],
              status: 'error' as const,
              step: data.message || 'Unknown error',
              error: data.message || 'Unknown error',
            },
          }));
          // Clear timeout
          if (pendingTimersRef.current[jid]) {
            clearTimeout(pendingTimersRef.current[jid]);
            delete pendingTimersRef.current[jid];
          }
          es.close();
        } catch { /* ignore */ }
      });

      // Native EventSource error (connection failure / close)
      es.addEventListener('error', () => {
        const errCount = (errorCountRef.current[jid] || 0) + 1;
        errorCountRef.current[jid] = errCount;

        if (es.readyState === EventSource.CLOSED) {
          // Connection permanently closed — won't retry
          setJobs(prev => {
            const current = prev[jid];
            if (current && current.status !== 'done' && current.status !== 'error') {
              return {
                ...prev,
                [jid]: { ...current, status: 'error' as const, error: 'Connection lost' },
              };
            }
            return prev;
          });
          // Clear timeout
          if (pendingTimersRef.current[jid]) {
            clearTimeout(pendingTimersRef.current[jid]);
            delete pendingTimersRef.current[jid];
          }
        } else if (errCount >= MAX_ERROR_COUNT) {
          // Still retrying but too many failures — give up
          setJobs(prev => {
            const current = prev[jid];
            if (current && current.status !== 'done' && current.status !== 'error') {
              return {
                ...prev,
                [jid]: { ...current, status: 'error' as const, error: `Connection failed after ${errCount} retries` },
              };
            }
            return prev;
          });
          es.close();
          // Clear timeout
          if (pendingTimersRef.current[jid]) {
            clearTimeout(pendingTimersRef.current[jid]);
            delete pendingTimersRef.current[jid];
          }
        }
        // else: EventSource is CONNECTING and retrying — let it retry
      });
    }

    return () => {
      for (const es of sources) {
        es.close();
      }
    };
  }, [jobIdsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Compute overall progress ---
  useEffect(() => {
    const entries = Object.values(jobs);
    if (entries.length === 0) return;

    let totalSteps = 0;
    let completedSteps = 0;
    let allDone = true;
    let hasActive = false;

    for (const j of entries) {
      const total = j.stepTotal || 8;
      totalSteps += total;
      if (j.status === 'done') {
        completedSteps += total;
      } else if (j.status === 'error') {
        completedSteps += total; // count as done for progress
      } else {
        allDone = false;
        hasActive = true;
        if (j.status === 'running') {
          completedSteps += j.stepIndex || 0;
        }
      }
    }

    setOverallProgress(totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0);
    setOverallDone(allDone && entries.length >= jobMetas.length && jobMetas.length > 0);
  }, [jobs, jobMetas.length, jobIdsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return { jobs, overallProgress, overallDone };
}
