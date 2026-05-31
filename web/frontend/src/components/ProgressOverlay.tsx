/* Analysis progress — slides down when jobs start, tighter job cards */

import type { JobProgress } from '../hooks/useSSE';

interface Props {
  jobs: Record<string, JobProgress>;
  overallProgress: number;
  overallDone: boolean;
}

const STEPS = [
  'Fetching PR data',
  'Processing changes',
  'Optimizing input',
  'Building prompt',
  'AI analysis',
  'Parsing results',
  'Saving results',
  'Finalizing',
];

function stepIndex(step: string) {
  for (let i = 0; i < STEPS.length; i++) {
    if (step.toLowerCase().includes(STEPS[i].toLowerCase().split(' ')[0])) return i;
  }
  return -1;
}

function StepTimeline({ job }: { job: JobProgress }) {
  const cur    = stepIndex(job.step);
  const active = job.status === 'running';
  const done   = job.status === 'done';

  return (
    <div className="grid gap-px mt-2" style={{ gridTemplateColumns: 'repeat(8, 1fr)' }}>
      {STEPS.map((label, i) => {
        const past    = active && i < cur;
        const current = active && i === cur;
        const color   = past || done  ? 'var(--color-success)' :
                        current       ? 'var(--color-primary)' :
                                        'var(--color-border)';
        return (
          <div
            key={label}
            title={label}
            style={{
              height: 3,
              borderRadius: 9999,
              background: color,
              transition: 'background 300ms ease',
            }}
          />
        );
      })}
    </div>
  );
}

function JobCard({ job }: { job: JobProgress }) {
  const borderColor: Record<string, string> = {
    pending: 'var(--color-border)',
    running: 'oklch(0.66 0.17 268 / 0.3)',
    done:    'oklch(0.65 0.16 152 / 0.25)',
    error:   'oklch(0.60 0.20 22 / 0.25)',
  };
  const bgColor: Record<string, string> = {
    pending: 'transparent',
    running: 'oklch(0.66 0.17 268 / 0.04)',
    done:    'oklch(0.65 0.16 152 / 0.03)',
    error:   'oklch(0.60 0.20 22 / 0.04)',
  };
  const dotClass: Record<string, string> = {
    pending: 'bg-faint',
    running: 'bg-primary animate-pulse-subtle',
    done:    'bg-success',
    error:   'bg-error',
  };

  return (
    <div
      className="rounded-lg p-3 transition-all duration-300"
      style={{
        border: `1px solid ${borderColor[job.status] ?? borderColor.pending}`,
        background: bgColor[job.status] ?? bgColor.pending,
      }}
    >
      {/* Header row */}
      <div className="flex items-center gap-2">
        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotClass[job.status] ?? dotClass.pending}`} />
        <span className="text-sm font-medium text-ink font-mono flex-1 min-w-0 truncate">
          {job.repo}#{job.prNumber}
        </span>
        <span className="text-xs flex-shrink-0">
          {job.status === 'running' && <span className="text-primary">running</span>}
          {job.status === 'done'    && <span className="text-success">done</span>}
          {job.status === 'error'   && <span className="text-error">failed</span>}
          {job.status === 'pending' && <span className="text-faint">queued</span>}
        </span>
      </div>

      {/* Step progress bar */}
      <StepTimeline job={job} />

      {/* Current step label */}
      {job.status === 'running' && job.step && (
        <p className="text-xs text-primary mt-1.5 truncate">{job.step}</p>
      )}

      {/* Error */}
      {job.status === 'error' && job.error && (
        <p className="text-xs text-error/80 mt-1.5 truncate">{job.error}</p>
      )}

      {/* Done summary */}
      {job.status === 'done' && job.resultSummary && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          <span className="badge badge-success">{job.resultSummary.findings_count} findings</span>
          {job.resultSummary.meta && (
            <>
              <span className="badge badge-info tabular-nums">
                {((job.resultSummary.meta as Record<string, unknown>).tokens_used as number ?? 0).toLocaleString()} tok
              </span>
              <span className="badge badge-low tabular-nums">
                {(() => {
                  const ms = (job.resultSummary.meta as Record<string, unknown>).duration_ms as number || 0;
                  return ms > 60000 ? `${(ms / 60000).toFixed(1)}m` : `${(ms / 1000).toFixed(1)}s`;
                })()}
              </span>
            </>
          )}
          {job.resultSummary.merge_readiness && (() => {
            const sc = (job.resultSummary.merge_readiness as Record<string, unknown>).score as number;
            const cls = sc >= 70 ? 'badge-success' : sc >= 40 ? 'badge-high' : 'badge-critical';
            return <span className={`badge ${cls} tabular-nums`}>{sc}/100</span>;
          })()}
        </div>
      )}
    </div>
  );
}

export default function ProgressOverlay({ jobs, overallProgress, overallDone }: Props) {
  const jobList     = Object.values(jobs);
  const runningCnt  = jobList.filter(j => j.status === 'running' || j.status === 'pending').length;
  const doneCnt     = jobList.filter(j => j.status === 'done').length;
  const errorCnt    = jobList.filter(j => j.status === 'error').length;
  const totalTokens = jobList.reduce((s, j) => {
    if (j.resultSummary?.meta) return s + ((j.resultSummary.meta as Record<string, unknown>).tokens_used as number || 0);
    return s;
  }, 0);

  if (jobList.length === 0) return null;

  return (
    <div className="card space-y-3 animate-slide-down">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            {overallDone ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" className="text-success">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink">
              {overallDone
                ? 'Analysis complete'
                : `Analyzing ${jobList.length} PR${jobList.length !== 1 ? 's' : ''}...`}
            </h3>
            <p className="text-xs text-muted">
              {runningCnt > 0 && `${runningCnt} running · `}
              {doneCnt} done{errorCnt > 0 ? ` · ${errorCnt} failed` : ''}
              {overallDone && totalTokens > 0 && ` · ${totalTokens.toLocaleString()} tokens`}
            </p>
          </div>
        </div>
        {!overallDone && (
          <span className="text-xl font-semibold text-primary tabular-nums">{overallProgress}%</span>
        )}
      </div>

      {/* Overall progress bar */}
      {!overallDone && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${overallProgress}%` }} />
        </div>
      )}

      {/* Per-job cards */}
      <div className={`grid gap-2.5 ${jobList.length > 1 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1'}`}>
        {jobList.map(job => <JobCard key={job.jobId} job={job} />)}
      </div>

      {/* Token total */}
      {totalTokens > 0 && (
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <span className="text-xs text-muted">Total tokens used</span>
          <span className="text-xs text-accent font-mono tabular-nums">{totalTokens.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
