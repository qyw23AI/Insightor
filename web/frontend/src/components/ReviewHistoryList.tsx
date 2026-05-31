/* Review history: published / draft split view */

import type { ReviewSummary } from '../types/urf';
import ReviewCard from './ReviewCard';

interface Props {
  reviews: ReviewSummary[];
  onSelect: (review: ReviewSummary) => void;
  onDelete?: (id: string) => void;
  activeId?: string;
}

export default function ReviewHistoryList({ reviews, onSelect, onDelete, activeId }: Props) {
  const published = reviews.filter(r => r.published && r.status === 'done');
  const drafts = reviews.filter(r => !r.published && r.status === 'done');

  if (reviews.length === 0) {
    return (
      <div className="empty-state card">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-faint mb-3">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        <p className="text-base text-muted">No review history yet</p>
        <p className="text-xs text-faint mt-1">Start your first analysis above</p>
      </div>
    );
  }

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (onDelete) onDelete(id);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Published */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-success flex items-center gap-2">
          Published
          <span className="text-faint font-normal">({published.length})</span>
        </h3>
        {published.length === 0 ? (
          <p className="text-xs text-faint py-4">No published reviews</p>
        ) : (
          published.slice(0, 5).map(r => (
            <ReviewCard key={r.id} review={r} active={activeId === r.id} onClick={() => onSelect(r)} />
          ))
        )}
      </div>

      {/* Drafts */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-accent flex items-center gap-2">
          Drafts
          <span className="text-faint font-normal">({drafts.length})</span>
        </h3>
        {drafts.length === 0 ? (
          <p className="text-xs text-faint py-4">No draft reviews</p>
        ) : (
          drafts.slice(0, 5).map(r => (
            <div key={r.id} className="relative group">
              <ReviewCard review={r} active={activeId === r.id} onClick={() => onSelect(r)} />
              {onDelete && (
                <button
                  onClick={(e) => handleDelete(e, r.id)}
                  className="absolute top-2 right-2 w-6 h-6 rounded-full bg-error/15 text-error hover:bg-error/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-150"
                  title="Delete draft"
                >
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
