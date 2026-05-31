/* Analysis progress — slides down when jobs start */

import type { JobProgress } from '../hooks/useSSE';

interface Props {
  jobs: Record<string, JobProgress>;
  overallProgress: number;
  overallDone: boolean;
}

const STEP_LABELS = [
  'Fetching PR data',
  'Processing changes',
  'Optimizing input',
  'Building prompt',
  'AI analysis',
  'Parsing results',
  'Saving results',
  'Finalizing',
];

function getStepIndex(step: string): number {
  for (let i = 0; i < STEP_LABELS.length; i++) {
    if (step.toLowerCase().includes(STEP_LABELS[i].toLowerCase().split(' ')[0])) return i;
  }
  return -1;
}

function StepTimeline({ job }: { job: JobProgress }) {
  const currentIdx = getStepIndex(job.step);
  const isRunning = job.status === 'running';

  return (
    <div className="space-y-0.5 mt-2">
      {STEP_LABELS.map((label, i) => {
        const isPast = isRunning && i < currentIdx;
        const isCurrent = isRunning && i === currentIdx;
        const isDone = job.status === 'done';

        return (
          <div
            key={label}
            className={`flex items-center gap-2 px-1 py-0.5 rounded text-sm transition-colors ${
              isPast || isDone ? 'text-success/70' :
              isCurrent ? 'text-primary' :
              'text-faint/40'
            }`}
          >
            <span className="w-3 text-center flex-shrink-0">
              {isPast || isDone ? '✓' :
               isCurrent ? '●' :
               '·'}
            </span>
            <span className="flex-1 truncate">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

function JobCard({ job }: { job: JobProgress }) {
  const statusBorder: Record<string, string> = {
    pending: 'border-border',
    running: 'border-primary/25',
    done: 'border-success/20',
    error: 'border-error/20',
  };

  const statusBg: Record<string, string> = {
    pending: 'bg-app-surface',
    running: 'bg-primary/4',
    done: 'bg-success/3',
    error: 'bg-error/3',
  };

  const dotColor: Record<string, string> = {
    pending: 'bg-faint',
    running: 'bg-primary animate-pulse-subtle',
    done: 'bg-success',
    error: 'bg-error',
  };

  return (
    <div className={`border rounded-lg p-4 transition-all duration-300 ${statusBorder[job.status] || statusBorder.pending} ${statusBg[job.status] || statusBg.pending}`}>
      {/* Header */}
      <div className="flex items-center gap-2.5 mb-3">
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${dotColor[job.status] || dotColor.pending}`} />
        <span className="text-base font-medium text-ink font-mono truncate">
          {job.repo}#{job.prNumber}
        </span>
        <span className="text-sm ml-auto flex-shrink-0">
          {job.status === 'running' && <span className="text-primary">running</span>}
          {job.status === 'done' && <span className="text-success">Done</span>}
          {job.status === 'error' && <span className="text-error">Failed</span>}
          {job.status === 'pending' && <span className="text-faint">queued</span>}
        </span>
      </div>

      {/* Step timeline */}
      <StepTimeline job={job} />

      {/* Error message */}
      {job.status === 'error' && job.error && (
        <p className="mt-2 text-sm text-error/80 truncate">{job.error}</p>
      )}

      {/* Findings counter */}
      {job.findings.length > 0 && (
        <div className="mt-2 text-sm text-primary">
          {job.findings.length} finding{job.findings.length > 1 ? 's' : ''} so far
        </div>
      )}

      {/* Result summary for done jobs */}
      {job.status === 'done' && job.resultSummary && (
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          <span className="px-2 py-0.5 rounded bg-app-surface-high text-success">
            {job.resultSummary.findings_count} findings
          </span>
          {job.resultSummary.meta && (
            <>
              <span className="px-2 py-0.5 rounded bg-app-surface-high text-accent tabular-nums">
                {(job.resultSummary.meta as Record<string, unknown>).tokens_used as number ?? 0} tokens
              </span>
              <span className="px-2 py-0.5 rounded bg-app-surface-high text-muted tabular-nums">
                {(() => {
                  const ms = (job.resultSummary.meta as Record<string, unknown>).duration_ms as number || 0;
                  return ms > 60000 ? `${(ms / 60000).toFixed(1)}m` : `${(ms / 1000).toFixed(1)}s`;
                })()}
              </span>
            </>
          )}
          {job.resultSummary.merge_readiness && (
            <span className={`px-2 py-0.5 rounded text-white tabular-nums ${
              (job.resultSummary.merge_readiness as Record<string, unknown>).score as number >= 70
                ? 'bg-success/25'
                : (job.resultSummary.merge_readiness as Record<string, unknown>).score as number >= 40
                ? 'bg-warning/25'
                : 'bg-error/25'
            }`}>
              Score: {String((job.resultSummary.merge_readiness as Record<string, unknown>).score)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProgressOverlay({ jobs, overallProgress, overallDone }: Props) {
  const jobList = Object.values(jobs);
  const runningCount = jobList.filter(j => j.status === 'running' || j.status === 'pending').length;
  const doneCount = jobList.filter(j => j.status === 'done').length;
  const errorCount = jobList.filter(j => j.status === 'error').length;
  const totalTokens = jobList.reduce((sum, j) => {
    if (j.resultSummary?.meta) {
      return sum + ((j.resultSummary.meta as Record<string, unknown>).tokens_used as number || 0);
    }
    return sum;
  }, 0);

  if (jobList.length === 0) return null;

  return (
    <div className="card space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            {overallDone ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-success"><polyline points="20 6 9 17 4 12" /></svg>
            ) : (
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-ink text-base">
              {overallDone
                ? 'Analysis complete'
                : `Analyzing ${jobList.length} PR${jobList.length > 1 ? 's' : ''}...`}
            </h3>
            <p className="text-sm text-muted">
              {runningCount > 0 && `${runningCount} running · `}
              {doneCount} done · {errorCount} failed
              {overallDone && totalTokens > 0 && ` · ${totalTokens.toLocaleString()} tokens used`}
            </p>
          </div>
        </div>
        {!overallDone && (
          <div className="text-right">
            <div className="text-2xl font-semibold text-primary tabular-nums">{overallProgress}%</div>
            <div className="text-sm text-muted">complete</div>
          </div>
        )}
      </div>

      {/* Overall progress bar */}
      {!overallDone && (
        <div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
          {jobList.length > 1 && (
            <div className="flex justify-between mt-1.5 px-0.5">
              {jobList.map((j) => (
                <div
                  key={j.jobId}
                  className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${
                    j.status === 'done' ? 'bg-success' :
                    j.status === 'error' ? 'bg-error' :
                    j.status === 'running' ? 'bg-primary animate-pulse-subtle' :
                    'bg-border'
                  }`}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Per-job cards */}
      <div className={`grid gap-3 ${jobList.length > 1 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
        {jobList.map(job => (
          <JobCard key={job.jobId} job={job} />
        ))}
      </div>

      {/* Token usage summary */}
      {totalTokens > 0 && (
        <div className="flex items-center justify-between pt-3 border-t border-border text-base">
          <span className="text-muted">Total tokens</span>
          <span className="text-accent font-mono font-medium tabular-nums">{totalTokens.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
