/* Review detail page — findings, diff, publish */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getReview, publishReview } from '../api/client';
import { useAuth } from '../context/AuthContext';
import FindingCard from '../components/FindingCard';
import FeedbackPanel from '../components/FeedbackPanel';
import DiffViewer, { fileAnchorId } from '../components/DiffViewer';
import ScoreGauge from '../components/ScoreGauge';
import type { Finding, FeedbackItem, FileWalkthrough } from '../types/urf';

function LoadingSkeleton() {
  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="space-y-2">
        <div className="skeleton h-4 w-16" />
        <div className="skeleton h-7 w-56" />
        <div className="skeleton h-4 w-40" />
      </div>
      <div className="card space-y-3">
        <div className="skeleton h-5 w-20" />
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
      </div>
      <div className="flex gap-3">
        <div className="skeleton h-9 w-24" />
        <div className="skeleton h-9 w-24" />
      </div>
      <div className="space-y-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="card space-y-3">
            <div className="flex gap-2">
              <div className="skeleton h-5 w-8" />
              <div className="skeleton h-5 w-14" />
              <div className="skeleton h-5 w-12" />
            </div>
            <div className="skeleton h-5 w-3/4" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ReviewDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [review, setReview] = useState<Record<string, unknown> | null>(null);
  const [diff, setDiff] = useState('');
  const [feedbacks, setFeedbacksState] = useState<Record<string, FeedbackItem>>({});
  const [published, setPublished] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [tab, setTab] = useState<'findings' | 'diff'>('findings');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [jumpToFile, setJumpToFile] = useState<string | null>(null);
  const jumpTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    if (!token || !id) return;
    try {
      const data = await getReview(token, id);
      setReview(data.review);
      setDiff(data.diff || '');
      setPublished(data.published);
      if (data.feedbacks) {
        const fb: Record<string, FeedbackItem> = {};
        for (const [fid, val] of Object.entries(data.feedbacks)) {
          fb[fid] = val as FeedbackItem;
        }
        setFeedbacksState(fb);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [token, id]);

  useEffect(() => { load(); }, [load]);

  const handleFeedbackChange = (item: FeedbackItem) => {
    setFeedbacksState(prev => ({ ...prev, [item.finding_id]: item }));
  };

  const handlePublish = async () => {
    if (!token || !id) return;
    setPublishing(true);
    try {
      const items = Object.values(feedbacks).filter(f => f.status);
      await publishReview(token, id, items);
      setPublished(true);
    } catch (e: unknown) {
      alert(`Publish failed: ${e instanceof Error ? e.message : 'Unknown error'}`);
    }
    setPublishing(false);
  };

  const handleJumpToFile = (filePath: string) => {
    setTab('diff');
    setJumpToFile(filePath);
  };

  useEffect(() => {
    if (!jumpToFile || tab !== 'diff') return;
    const anchorId = fileAnchorId(jumpToFile);
    const frameId = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const el = document.getElementById(anchorId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          el.classList.add('ring-spot');
          if (jumpTimeoutRef.current) clearTimeout(jumpTimeoutRef.current);
          jumpTimeoutRef.current = setTimeout(() => {
            el.classList.remove('ring-spot');
            setJumpToFile(null);
          }, 2000);
        } else {
          setJumpToFile(null);
        }
      });
    });
    return () => {
      if (jumpTimeoutRef.current) clearTimeout(jumpTimeoutRef.current);
    };
  }, [jumpToFile, tab]);

  useEffect(() => {
    return () => {
      if (jumpTimeoutRef.current) clearTimeout(jumpTimeoutRef.current);
    };
  }, []);

  if (loading) return <LoadingSkeleton />;

  if (!review) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-full gap-4">
        <div className="w-16 h-16 rounded-2xl bg-app-surface flex items-center justify-center border border-border">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-faint">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <p className="text-muted text-sm font-medium">Review not found</p>
        <button onClick={() => navigate('/dashboard')} className="btn-ghost text-sm">Back to dashboard</button>
      </div>
    );
  }

  const findings: Finding[] = (review.findings as Finding[]) || [];
  const meta = review.meta as Record<string, unknown> | null;
  const mr = review.merge_readiness as Record<string, unknown> | null;
  const summary = review.summary as Record<string, unknown> | null;
  const fileWalkthrough: FileWalkthrough[] = (review.file_walkthrough as FileWalkthrough[]) || [];

  const filteredFindings = severityFilter === 'all'
    ? findings
    : findings.filter(f => f.severity === severityFilter);

  const sevs = ['critical', 'high', 'medium', 'low', 'info'];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <button onClick={() => navigate('/dashboard')} className="btn-ghost text-sm mb-2">
            &larr; Back
          </button>
          <h1 className="text-lg font-semibold text-ink tracking-tight">
            #{meta?.pr_url ? (meta.pr_url as string).split('/').pop() : id?.slice(0, 8)}
          </h1>
          <p className="text-sm text-muted mt-1">
            {meta?.model as string} &middot; {meta?.analysis_depth as string} &middot; {meta?.duration_ms ? `${(meta.duration_ms as number / 1000).toFixed(0)}s` : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {mr?.score !== undefined && (
            <ScoreGauge score={mr.score as number} recommendation={(mr.recommendation as string) || ''} />
          )}
          {published ? (
            <span className="badge badge-success text-xs">
              Published
            </span>
          ) : (
            <button onClick={handlePublish} disabled={publishing} className="btn-primary">
              {publishing ? 'Publishing...' : 'Publish to GitHub'}
            </button>
          )}
        </div>
      </div>

      {/* Summary card */}
      {summary && (
        <div className="card">
          <h3 className="font-semibold text-ink text-sm mb-2">Summary</h3>
          <p className="text-sm text-muted leading-relaxed">{summary.overview as string}</p>
          <div className="flex items-center gap-3 mt-3 text-xs text-faint">
            <span>{summary.pr_type as string}</span>
            <span>&middot;</span>
            <span>{summary.files_changed as number} files (+{summary.additions as number} / -{summary.deletions as number})</span>
          </div>

          {/* File walkthrough */}
          {fileWalkthrough.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border">
              <h4 className="text-xs font-medium text-muted mb-2">
                Changed files ({fileWalkthrough.length})
              </h4>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {fileWalkthrough.map((fw, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs group hover:bg-app-surface-elevated rounded-md px-1.5 py-1 -mx-1.5 transition-colors">
                    <span className={`mt-0.5 w-4 text-center flex-shrink-0 font-mono text-2xs ${
                      fw.edit_type === 'added' ? 'text-success' :
                      fw.edit_type === 'deleted' ? 'text-error' :
                      fw.edit_type === 'renamed' ? 'text-warning' :
                      'text-accent'
                    }`}>
                      {fw.edit_type === 'added' ? '+' : fw.edit_type === 'deleted' ? '−' : fw.edit_type === 'renamed' ? '↻' : '~'}
                    </span>
                    <code className="text-muted flex-1 min-w-0 truncate text-2xs">{fw.path}</code>
                    {fw.summary && (
                      <span className="text-faint flex-shrink-0 hidden lg:inline truncate max-w-[240px] text-2xs">{fw.summary}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tabs: Findings / Diff */}
      <div className="flex border-b border-border gap-6">
        <button className={`tab ${tab === 'findings' ? 'active' : ''}`} onClick={() => setTab('findings')}>
          Findings ({findings.length})
        </button>
        <button className={`tab ${tab === 'diff' ? 'active' : ''}`} onClick={() => setTab('diff')}>
          Diff view
        </button>
      </div>

      {/* Severity filter */}
      {tab === 'findings' && (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setSeverityFilter('all')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
              severityFilter === 'all'
                ? 'bg-primary text-white'
                : 'bg-app-surface text-muted hover:text-ink hover:bg-app-surface-elevated'
            }`}
          >
            All ({findings.length})
          </button>
          {sevs.map(s => {
            const count = findings.filter(f => f.severity === s).length;
            if (count === 0) return null;
            return (
              <button
                key={s}
                onClick={() => setSeverityFilter(s)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 capitalize ${
                  severityFilter === s
                    ? 'bg-primary text-white'
                    : 'bg-app-surface text-muted hover:text-ink hover:bg-app-surface-elevated'
                }`}
              >
                {s} ({count})
              </button>
            );
          })}
        </div>
      )}

      {/* Findings list */}
      {tab === 'findings' && (
        <div className="space-y-4">
          {filteredFindings.length === 0 ? (
            <div className="empty-state">
              <p className="text-sm text-muted">No findings in this category</p>
            </div>
          ) : (
            filteredFindings.map((f, i) => (
              <FindingCard
                key={f.id}
                finding={f}
                index={i}
                showFeedback
                onJumpToFile={handleJumpToFile}
                feedbackUI={
                  <FeedbackPanel
                    finding={f}
                    onChange={handleFeedbackChange}
                    initial={feedbacks[f.id] || null}
                  />
                }
              />
            ))
          )}
        </div>
      )}

      {/* Diff view */}
      {tab === 'diff' && (
        <div className="card !p-0 overflow-hidden">
          {diff ? (
            <div className="p-5">
              <DiffViewer diffText={diff} scrollToFile={jumpToFile} onScrollDone={() => setJumpToFile(null)} />
            </div>
          ) : (
            <div className="empty-state">
              <p className="text-sm text-muted">No diff available for this review</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
