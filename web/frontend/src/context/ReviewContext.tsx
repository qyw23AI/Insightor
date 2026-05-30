/* Review context — keeps running jobs + SSE connections alive across page navigation */

import React, { createContext, useCallback, useContext, useState } from 'react';
import { useMultiSSE } from '../hooks/useSSE';
import type { JobProgress } from '../hooks/useSSE';

export interface RunningJob {
  job_id: string;
  pr_url: string;
  pr_number: number;
  repo?: string;
  tool?: string;
  depth?: string;
  status?: string;
  error?: string | null;
}

interface ReviewState {
  runningJobs: RunningJob[];
  jobs: Record<string, JobProgress>;
  overallProgress: number;
  overallDone: boolean;
  isRunning: boolean;
  startJobs: (jobs: RunningJob[]) => void;
  clearJobs: () => void;
}

const ReviewContext = createContext<ReviewState>({
  runningJobs: [],
  jobs: {},
  overallProgress: 0,
  overallDone: false,
  isRunning: false,
  startJobs: () => {},
  clearJobs: () => {},
});

export function ReviewProvider({ children }: { children: React.ReactNode }) {
  const [runningJobs, setRunningJobs] = useState<RunningJob[]>([]);

  // SSE stays connected as long as this provider is mounted (across page nav)
  const { jobs, overallProgress, overallDone } = useMultiSSE(runningJobs);

  const startJobs = useCallback((newJobs: RunningJob[]) => {
    setRunningJobs(newJobs);
  }, []);

  const clearJobs = useCallback(() => {
    setRunningJobs([]);
  }, []);

  const isRunning = runningJobs.length > 0 && !overallDone;

  return (
    <ReviewContext.Provider value={{ runningJobs, jobs, overallProgress, overallDone, isRunning, startJobs, clearJobs }}>
      {children}
    </ReviewContext.Provider>
  );
}

export function useReview() {
  return useContext(ReviewContext);
}
