/* Rich progress overlay with per-job cards, step timeline, and token usage */

import type { JobProgress } from '../hooks/useSSE';

interface Props {
  jobs: Record<string, JobProgress>;
  overallProgress: number;
  overallDone: boolean;
}

const STEP_ICONS: Record<string, string> = {
  '获取 PR 数据': '📥',
  '处理代码变更': '🔧',
  '优化输入': '⚙️',
  '构建分析提示': '📋',
  'AI 分析': '🤖',
  '解析分析结果': '🔍',
  '保存结果': '💾',
  '输出结果': '📊',
};

const STEP_LABELS = [
  { key: '获取 PR 数据', label: '获取 PR 数据' },
  { key: '处理代码变更', label: '处理代码变更' },
  { key: '优化输入', label: '优化输入' },
  { key: '构建分析提示', label: '构建分析提示' },
  { key: 'AI 分析', label: 'AI 分析' },
  { key: '解析分析结果', label: '解析分析结果' },
  { key: '保存结果', label: '保存结果' },
  { key: '输出结果', label: '输出结果' },
];

function getStepIcon(step: string): string {
  for (const [key, icon] of Object.entries(STEP_ICONS)) {
    if (step.includes(key)) return icon;
  }
  return '⏳';
}

function getStepKey(step: string): string {
  for (const s of STEP_LABELS) {
    if (step.includes(s.key)) return s.key;
  }
  return '';
}

function StepTimeline({ job }: { job: JobProgress }) {
  const currentKey = getStepKey(job.step);
  const currentIdx = STEP_LABELS.findIndex(s => s.key === currentKey);
  const isRunning = job.status === 'running';

  return (
    <div className="space-y-0.5">
      {STEP_LABELS.map((s, i) => {
        const isPast = isRunning && i < currentIdx;
        const isCurrent = isRunning && i === currentIdx;
        const isFuture = isRunning && i > currentIdx;
        const isAllDone = job.status === 'done';

        return (
          <div
            key={s.key}
            className={`flex items-center gap-2 px-1 py-0.5 rounded text-xs transition-colors ${
              isPast || isAllDone ? 'text-green-400/70' :
              isCurrent ? 'text-blue-400' :
              'text-surface-200/25'
            }`}
          >
            <span className="w-4 text-center flex-shrink-0">
              {isPast || isAllDone ? '✓' :
               isCurrent ? <span className="inline-block animate-spin">⚡</span> :
               '·'}
            </span>
            <span className="flex-shrink-0 text-xs">{STEP_ICONS[s.key] || '⏳'}</span>
            <span className="flex-1 truncate">{s.label}</span>
          </div>
        );
      })}
    </div>
  );
}

function JobCard({ job }: { job: JobProgress }) {
  const statusColors: Record<string, string> = {
    pending: 'bg-surface-700 border-surface-600',
    running: 'bg-blue-600/10 border-blue-500/30',
    done: 'bg-green-600/10 border-green-500/30',
    error: 'bg-red-600/10 border-red-500/30',
  };

  const statusDot: Record<string, string> = {
    pending: 'bg-surface-400',
    running: 'bg-blue-400 animate-pulse',
    done: 'bg-green-400',
    error: 'bg-red-400',
  };

  return (
    <div className={`border rounded-xl p-4 transition-all duration-300 ${statusColors[job.status] || statusColors.pending}`}>
      {/* Header */}
      <div className="flex items-center gap-2.5 mb-3">
        <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${statusDot[job.status] || statusDot.pending}`} />
        <span className="text-sm font-semibold text-white truncate">
          {job.repo}#{job.prNumber}
        </span>
        {job.status === 'running' && (
          <span className="text-xs text-blue-400 ml-auto flex-shrink-0 animate-pulse">running</span>
        )}
        {job.status === 'done' && (
          <span className="text-xs text-green-400 ml-auto flex-shrink-0">✓ Done</span>
        )}
        {job.status === 'error' && (
          <span className="text-xs text-red-400 ml-auto flex-shrink-0">✗ Failed</span>
        )}
        {job.status === 'pending' && (
          <span className="text-xs text-surface-200/40 ml-auto flex-shrink-0">queued</span>
        )}
      </div>

      {/* Step timeline */}
      <StepTimeline job={job} />

      {/* Error message */}
      {job.status === 'error' && job.error && (
        <p className="mt-2 text-xs text-red-400/80 truncate">{job.error}</p>
      )}

      {/* Findings counter */}
      {job.findings.length > 0 && (
        <div className="mt-2 text-xs text-blue-400">
          🔎 {job.findings.length} finding{job.findings.length > 1 ? 's' : ''} so far
        </div>
      )}

      {/* Result summary for done jobs */}
      {job.status === 'done' && job.resultSummary && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="px-2 py-0.5 rounded bg-surface-700 text-green-400">
            {job.resultSummary.findings_count} findings
          </span>
          {job.resultSummary.meta && (
            <>
              <span className="px-2 py-0.5 rounded bg-surface-700 text-cyan-400">
                {String((job.resultSummary.meta as Record<string, unknown>).tokens_used ?? 0)} tokens
              </span>
              <span className="px-2 py-0.5 rounded bg-surface-700 text-purple-400">
                {(() => {
                  const ms = (job.resultSummary.meta as Record<string, unknown>).duration_ms as number || 0;
                  return ms > 60000 ? `${(ms / 60000).toFixed(1)}m` : `${(ms / 1000).toFixed(1)}s`;
                })()}
              </span>
            </>
          )}
          {job.resultSummary.merge_readiness && (
            <span className={`px-2 py-0.5 rounded text-white ${
              (job.resultSummary.merge_readiness as Record<string, unknown>).score as number >= 70
                ? 'bg-green-600/30'
                : (job.resultSummary.merge_readiness as Record<string, unknown>).score as number >= 40
                ? 'bg-yellow-600/30'
                : 'bg-red-600/30'
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
    <div className="card space-y-4 animate-in fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center">
            {overallDone ? (
              <span className="text-xl">✅</span>
            ) : runningCount > 0 ? (
              <span className="animate-spin text-xl">⚡</span>
            ) : (
              <span className="text-xl">📊</span>
            )}
          </div>
          <div>
            <h3 className="font-semibold text-white text-lg">
              {overallDone
                ? `Analysis Complete`
                : `Analyzing ${jobList.length} PR${jobList.length > 1 ? 's' : ''}...`}
            </h3>
            <p className="text-sm text-surface-200/50">
              {runningCount > 0 && `${runningCount} running · `}
              {doneCount} done · {errorCount} failed
              {overallDone && totalTokens > 0 && ` · ${totalTokens.toLocaleString()} tokens used`}
            </p>
          </div>
        </div>
        {!overallDone && (
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-400">{overallProgress}%</div>
            <div className="text-xs text-surface-200/50">complete</div>
          </div>
        )}
      </div>

      {/* Overall progress bar */}
      {!overallDone && (
        <div>
          <div className="h-2.5 bg-surface-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-400 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
          {/* Tick marks */}
          {jobList.length > 1 && (
            <div className="flex justify-between mt-1.5">
              {jobList.map((j, i) => (
                <div
                  key={j.jobId}
                  className={`w-2 h-2 rounded-full transition-colors duration-300 ${
                    j.status === 'done' ? 'bg-green-400' :
                    j.status === 'error' ? 'bg-red-400' :
                    j.status === 'running' ? 'bg-blue-400 animate-pulse' :
                    'bg-surface-600'
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
        <div className="flex items-center justify-between pt-3 border-t border-surface-700 text-sm">
          <span className="text-surface-200/60">Total tokens</span>
          <span className="text-cyan-400 font-mono font-semibold">{totalTokens.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
