/* Main dashboard page with multi-job support */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { addPREntries, getPREntries, getReviews, deleteReview, startAnalysis, deletePREntry } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useReview } from '../context/ReviewContext';
import type { RunningJob } from '../context/ReviewContext';
import PRInput from '../components/PRInput';
import PREntryList from '../components/PREntryList';
import ReviewHistoryList from '../components/ReviewHistoryList';
import ProgressOverlay from '../components/ProgressOverlay';
import type { PREntry, ReviewSummary } from '../types/urf';

export default function DashboardPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [entries, setEntries] = useState<PREntry[]>([]);
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [selectedReview, setSelectedReview] = useState<ReviewSummary | null>(null);

  // Running jobs + SSE live in ReviewContext — survives page navigation
  const { jobs, overallProgress, overallDone, isRunning, runningJobs, startJobs, clearJobs } = useReview();

  const loadData = useCallback(async () => {
    if (!token) return;
    const [ent, rev] = await Promise.all([getPREntries(token), getReviews(token)]);
    setEntries(ent);
    setReviews(rev);
  }, [token]);

  useEffect(() => { loadData(); }, [loadData]);

  // When all jobs complete, refresh data and clear running jobs after a delay
  useEffect(() => {
    if (overallDone && runningJobs.length > 0) {
      // SSE "done" is now published AFTER DB commit, so data is ready immediately.
      loadData();
      // Keep the progress visible for a moment, then clear
      const timer = setTimeout(() => {
        clearJobs();
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [overallDone, runningJobs.length]);

  // Import PRs only — save entries, no analysis
  const handleImport = async (urls: string[]) => {
    if (!token) return;
    try {
      await addPREntries(token, urls);
      loadData();
    } catch (e: unknown) {
      console.error('Import error:', e);
    }
  };

  // Quick shortcut: import + analyze immediately
  const handleAnalyze = async (urls: string[], tool: string, depth: string, model?: string) => {
    if (!token) return;
    try {
      await addPREntries(token, urls);
      const result = await startAnalysis(token, urls, tool, depth, model);
      const jobs: RunningJob[] = (result.jobs || []).map((j: { job_id: string; pr_url: string; pr_number: number }) => ({
        job_id: j.job_id,
        pr_url: j.pr_url,
        pr_number: j.pr_number,
        repo: j.pr_url.match(/github\.com\/([^/]+\/[^/]+)\/pull\//)?.[1] || '',
        tool,
        depth,
        status: 'pending',
      }));
      startJobs(jobs);
      loadData();
    } catch (e: unknown) {
      console.error('Analysis error:', e);
    }
  };

  // Batch review: start analysis on already-imported PRs
  const handleBatchReview = async (urls: string[], tool: string, depth: string, model?: string) => {
    if (!token || urls.length === 0) return;
    try {
      const result = await startAnalysis(token, urls, tool, depth, model);
      const jobs: RunningJob[] = (result.jobs || []).map((j: { job_id: string; pr_url: string; pr_number: number }) => ({
        job_id: j.job_id,
        pr_url: j.pr_url,
        pr_number: j.pr_number,
        repo: j.pr_url.match(/github\.com\/([^/]+\/[^/]+)\/pull\//)?.[1] || '',
        tool,
        depth,
        status: 'pending',
      }));
      startJobs(jobs);
      loadData();
    } catch (e: unknown) {
      console.error('Batch review error:', e);
    }
  };

  const handleDeleteEntry = async (id: string) => {
    if (!token) return;
    await deletePREntry(token, id);
    loadData();
  };

  const handleDeleteReview = async (id: string) => {
    if (!token) return;
    try {
      await deleteReview(token, id);
      loadData();
    } catch (e: unknown) {
      console.error('Delete review error:', e);
    }
  };

  const handleSelectReview = (review: ReviewSummary) => {
    setSelectedReview(review);
    navigate(`/review/${review.id}`);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-surface-200/60">PR Review Console</p>
        </div>
        {reviews.length > 0 && (
          <div className="text-sm text-surface-200/40">
            {reviews.filter(r => r.published).length} published · {reviews.filter(r => !r.published && r.status === 'done').length} drafts
          </div>
        )}
      </div>

      <PRInput onSubmit={handleAnalyze} onImport={handleImport} disabled={isRunning} />

      {/* Rich multi-job progress display */}
      {runningJobs.length > 0 && (
        <ProgressOverlay
          jobs={jobs}
          overallProgress={overallProgress}
          overallDone={overallDone}
        />
      )}

      <PREntryList
        entries={entries}
        onBatchReview={handleBatchReview}
        onDelete={handleDeleteEntry}
        disabled={isRunning}
      />

      <ReviewHistoryList reviews={reviews} onSelect={handleSelectReview} onDelete={handleDeleteReview} activeId={selectedReview?.id} />
    </div>
  );
}
