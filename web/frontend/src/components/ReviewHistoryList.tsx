/* Review history: published / unpublished split view */

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
  const unpublished = reviews.filter(r => !r.published && r.status === 'done');

  if (reviews.length === 0) {
    return (
      <div className="card text-center py-8">
        <p className="text-surface-200/50">No review history yet. Start your first analysis above!</p>
      </div>
    );
  }

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (onDelete) onDelete(id);
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-green-400 flex items-center gap-2">
          ✅ Published <span className="text-xs text-surface-200/50">({published.length})</span>
        </h3>
        {published.length === 0 ? (
          <p className="text-xs text-surface-200/40 py-4">No published reviews</p>
        ) : (
          published.slice(0, 5).map(r => (
            <ReviewCard key={r.id} review={r} active={activeId === r.id} onClick={() => onSelect(r)} />
          ))
        )}
      </div>
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-yellow-400 flex items-center gap-2">
          📝 Drafts <span className="text-xs text-surface-200/50">({unpublished.length})</span>
        </h3>
        {unpublished.length === 0 ? (
          <p className="text-xs text-surface-200/40 py-4">No draft reviews</p>
        ) : (
          unpublished.slice(0, 5).map(r => (
            <div key={r.id} className="relative group">
              <ReviewCard review={r} active={activeId === r.id} onClick={() => onSelect(r)} />
              {onDelete && (
                <button
                  onClick={(e) => handleDelete(e, r.id)}
                  className="absolute top-2 right-2 w-6 h-6 rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/40 flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Delete draft"
                >
                  ✕
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
