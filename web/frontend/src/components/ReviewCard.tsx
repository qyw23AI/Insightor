/* Review summary card */

import type { ReviewSummary } from '../types/urf';

interface Props {
  review: ReviewSummary;
  active?: boolean;
  onClick: () => void;
}

export default function ReviewCard({ review, active, onClick }: Props) {
  const date = review.completed_at
    ? new Date(review.completed_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div
      onClick={onClick}
      className={`card cursor-pointer transition-all ${
        active ? 'border-blue-500/50 bg-blue-600/5' : 'hover:border-surface-200/30'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="font-semibold text-white text-sm">#{review.pr_number}</h4>
          <p className="text-xs text-surface-200/50 mt-0.5">{review.tool} · {review.depth}</p>
        </div>
        <div className="flex items-center gap-2">
          {review.published ? (
            <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400">Published</span>
          ) : review.status === 'done' ? (
            <span className="text-xs px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400">Draft</span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded bg-surface-700 text-surface-200/50">{review.status}</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4 mt-3 text-xs text-surface-200/60">
        {review.score !== null && (
          <span className={`font-mono font-bold ${
            review.score >= 80 ? 'text-green-400' : review.score >= 50 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {review.score}/100
          </span>
        )}
        <span>{review.findings_count} findings</span>
        <span>{(review.duration_ms / 1000).toFixed(0)}s</span>
      </div>
      {date && <p className="text-xs text-surface-200/40 mt-2">{date}</p>}
    </div>
  );
}
