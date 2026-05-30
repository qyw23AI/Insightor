/* Review detail page with findings + diff */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getReview, publishReview } from '../api/client';
import { useAuth } from '../context/AuthContext';
import FindingCard from '../components/FindingCard';
import FeedbackPanel from '../components/FeedbackPanel';
import DiffViewer, { fileAnchorId } from '../components/DiffViewer';
import ScoreGauge from '../components/ScoreGauge';
import type { Finding, FeedbackItem, FileWalkthrough } from '../types/urf';

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

  // Scroll to file anchor after tab switches to diff and DOM renders
  useEffect(() => {
    if (!jumpToFile || tab !== 'diff') return;
    const anchorId = fileAnchorId(jumpToFile);
    // Wait for React to render the diff tab content
    const frameId = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        const el = document.getElementById(anchorId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Highlight the target file block
          el.classList.add('ring-2', 'ring-blue-500/50');
          if (jumpTimeoutRef.current) clearTimeout(jumpTimeoutRef.current);
          jumpTimeoutRef.current = setTimeout(() => {
            el.classList.remove('ring-2', 'ring-blue-500/50');
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

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (jumpTimeoutRef.current) clearTimeout(jumpTimeoutRef.current);
    };
  }, []);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <p className="text-surface-200/40">Loading review...</p>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-full gap-4">
        <p className="text-surface-200/40">Review not found</p>
        <button onClick={() => navigate('/dashboard')} className="btn-ghost">Back to Dashboard</button>
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
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <button onClick={() => navigate('/dashboard')} className="btn-ghost text-sm mb-2">← Back</button>
          <h1 className="text-xl font-bold text-white">
            Review #{meta?.pr_url ? (meta.pr_url as string).split('/').pop() : id?.slice(0, 8)}
          </h1>
          <p className="text-sm text-surface-200/60 mt-1">
            {meta?.model as string} · {meta?.analysis_depth as string} · {meta?.duration_ms ? `${(meta.duration_ms as number / 1000).toFixed(0)}s` : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {mr?.score !== undefined && (
            <ScoreGauge score={mr.score as number} recommendation={(mr.recommendation as string) || ''} />
          )}
          {published ? (
            <span className="px-3 py-1.5 rounded-lg bg-green-500/20 text-green-400 text-sm font-medium">Published</span>
          ) : (
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="btn-primary"
            >
              {publishing ? 'Publishing...' : '🚀 Publish to GitHub'}
            </button>
          )}
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="card">
          <h3 className="font-semibold text-white mb-2">Summary</h3>
          <p className="text-sm text-surface-200/80">{summary.overview as string}</p>
          <p className="text-xs text-surface-200/50 mt-1">
            {summary.pr_type as string} · {summary.files_changed as number} files changed (↑{summary.additions as number} ↓{summary.deletions as number})
          </p>

          {/* File changes list */}
          {fileWalkthrough.length > 0 && (
            <div className="mt-3 pt-3 border-t border-surface-700/50">
              <h4 className="text-xs font-semibold text-surface-200/60 mb-2 uppercase tracking-wide">
                Changed Files ({fileWalkthrough.length})
              </h4>
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {fileWalkthrough.map((fw, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs group hover:bg-surface-700/30 rounded px-1.5 py-1 -mx-1.5 transition-colors">
                    <span className={`mt-0.5 w-4 text-center flex-shrink-0 ${
                      fw.edit_type === 'added' ? 'text-green-400' :
                      fw.edit_type === 'deleted' ? 'text-red-400' :
                      fw.edit_type === 'renamed' ? 'text-yellow-400' :
                      'text-blue-400'
                    }`}>
                      {fw.edit_type === 'added' ? '+' : fw.edit_type === 'deleted' ? '−' : fw.edit_type === 'renamed' ? '↻' : '~'}
                    </span>
                    <code className="text-surface-200/90 flex-1 min-w-0 truncate">{fw.path}</code>
                    {fw.summary && (
                      <span className="text-surface-200/40 flex-shrink-0 hidden md:inline truncate max-w-[200px]">{fw.summary}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-surface-700 gap-4">
        <button className={`tab ${tab === 'findings' ? 'active' : ''}`} onClick={() => setTab('findings')}>
          Findings ({findings.length})
        </button>
        <button className={`tab ${tab === 'diff' ? 'active' : ''}`} onClick={() => setTab('diff')}>
          Diff View
        </button>
      </div>

      {tab === 'findings' && (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setSeverityFilter('all')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              severityFilter === 'all' ? 'bg-blue-600 text-white' : 'bg-surface-800 text-surface-200/60 hover:text-white'
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
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  severityFilter === s ? 'bg-blue-600 text-white' : 'bg-surface-800 text-surface-200/60 hover:text-white'
                }`}
              >
                {s.toUpperCase()} ({count})
              </button>
            );
          })}
        </div>
      )}

      {tab === 'findings' && (
        <div className="space-y-4">
          {filteredFindings.length === 0 ? (
            <div className="card text-center py-8">
              <p className="text-surface-200/50">No findings in this category.</p>
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

      {tab === 'diff' && (
        <div className="card">
          {diff ? (
            <DiffViewer
              diffText={diff}
              scrollToFile={jumpToFile}
              onScrollDone={() => setJumpToFile(null)}
            />
          ) : (
            <p className="text-center py-8 text-surface-200/50">No diff available for this review.</p>
          )}
        </div>
      )}
    </div>
  );
}
