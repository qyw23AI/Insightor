/* Review history — tabs (All / Drafts / Published) + unified list */

import { useState } from 'react';
import type { ReviewSummary } from '../types/urf';

interface Props {
  reviews: ReviewSummary[];
  onSelect: (review: ReviewSummary) => void;
  onDelete?: (id: string) => void;
  activeId?: string;
}

type Tab = 'all' | 'drafts' | 'published';

function repoSlug(url: string) {
  return url.match(/github\.com\/([^/]+\/[^/]+)/)?.[1] ?? '';
}

function shortDate(iso: string | null) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
}

function ScoreDot({ score }: { score: number | null }) {
  if (score == null) return <span className="text-sm text-faint tabular-nums">—</span>;
  const cls = score >= 80 ? 'text-success' : score >= 50 ? 'text-warning' : 'text-error';
  return <span className={`text-sm font-mono font-medium tabular-nums ${cls}`}>{score}</span>;
}

export default function ReviewHistoryList({ reviews, onSelect, onDelete, activeId }: Props) {
  const [tab, setTab] = useState<Tab>('all');

  const done      = reviews.filter(r => r.status === 'done');
  const published = done.filter(r => r.published);
  const drafts    = done.filter(r => !r.published);

  const counts: Record<Tab, number> = { all: done.length, drafts: drafts.length, published: published.length };
  const list = tab === 'published' ? published : tab === 'drafts' ? drafts : done;

  if (reviews.length === 0) {
    return (
      <div className="card">
        <div className="empty-state">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" className="text-faint mb-2.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <p className="text-base text-muted">No reviews yet</p>
          <p className="text-sm text-faint mt-0.5">Start your first analysis above</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card !p-0 overflow-hidden">
      {/* Tab bar */}
      <div className="flex border-b border-border px-1 pt-1">
        {(['all', 'drafts', 'published'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`tab capitalize${tab === t ? ' active' : ''}`}
          >
            {t}
            <span className="text-faint ml-1.5 tabular-nums">{counts[t]}</span>
          </button>
        ))}
      </div>

      {/* List */}
      {list.length === 0 ? (
        <p className="text-xs text-faint text-center py-6">No {tab} reviews</p>
      ) : (
        <div className="divide-y" style={{ borderColor: 'var(--color-border)', opacity: 1 }}>
          {list.map(r => {
            const slug = repoSlug(r.pr_url);
            const date = shortDate(r.completed_at);
            const isActive = activeId === r.id;

            return (
              <div
                key={r.id}
                onClick={() => onSelect(r)}
                className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors duration-100 group ${
                  isActive ? 'bg-primary/5' : 'hover:bg-app-surface-elevated'
                }`}
              >
                {/* Left: PR number + repo + meta */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-1.5 mb-0.5">
                    <span className="text-base font-mono font-medium text-ink leading-snug">
                      #{r.pr_number}
                    </span>
                    {slug && (
                      <span className="text-sm text-faint truncate leading-snug">{slug}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 text-sm text-faint leading-snug">
                    <span>{r.tool}</span>
                    <span>·</span>
                    <span>{r.depth}</span>
                    {date && <><span>·</span><span>{date}</span></>}
                    {r.duration_ms > 0 && (
                      <><span>·</span><span className="tabular-nums">{(r.duration_ms / 1000).toFixed(0)}s</span></>
                    )}
                  </div>
                </div>

                {/* Right: score + findings + status dot */}
                <div className="flex items-center gap-2.5 flex-shrink-0">
                  <ScoreDot score={r.score} />
                  <span className="text-xs text-faint tabular-nums">{r.findings_count}f</span>
                  <span
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                      r.published ? 'bg-success' : 'bg-border'
                    }`}
                    title={r.published ? 'Published' : 'Draft'}
                  />
                  {onDelete && !r.published && (
                    <button
                      onClick={ev => { ev.stopPropagation(); onDelete(r.id); }}
                      className="icon-btn danger opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Delete draft"
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
