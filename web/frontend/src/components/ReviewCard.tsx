/* Review summary card */

import type { ReviewSummary } from '../types/urf';

interface Props {
  review: ReviewSummary;
  active?: boolean;
  onClick: () => void;
}

export default function ReviewCard({ review, active, onClick }: Props) {
  const date = review.completed_at
    ? new Date(review.completed_at).toLocaleDateString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '';

  return (
    <div
      onClick={onClick}
      className={`${active ? 'card-active' : 'card-interactive'}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="font-medium text-ink text-base">#{review.pr_number}</h4>
          <p className="text-xs text-muted mt-0.5">{review.tool} &middot; {review.depth}</p>
        </div>
        <div className="flex items-center gap-2">
          {review.published ? (
            <span className="badge badge-success text-xs">Published</span>
          ) : review.status === 'done' ? (
            <span className="badge badge-info text-xs">Draft</span>
          ) : (
            <span className="badge badge-low text-xs">{review.status}</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4 mt-3 text-sm tabular-nums">
        {review.score !== null && (
          <span className={`font-mono font-medium ${
            review.score >= 80 ? 'text-success' : review.score >= 50 ? 'text-warning' : 'text-error'
          }`}>
            {review.score}/100
          </span>
        )}
        <span className="text-muted">{review.findings_count} findings</span>
        <span className="text-muted">{(review.duration_ms / 1000).toFixed(0)}s</span>
      </div>
      {date && <p className="text-xs text-faint mt-2">{date}</p>}
    </div>
  );
}
