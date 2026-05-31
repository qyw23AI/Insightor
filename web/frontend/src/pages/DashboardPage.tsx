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

  const { jobs, overallProgress, overallDone, isRunning, runningJobs, startJobs, clearJobs } = useReview();

  const loadData = useCallback(async () => {
    if (!token) return;
    const [ent, rev] = await Promise.all([getPREntries(token), getReviews(token)]);
    setEntries(ent);
    setReviews(rev);
  }, [token]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    if (overallDone && runningJobs.length > 0) {
      loadData();
      const timer = setTimeout(() => { clearJobs(); }, 8000);
      return () => clearTimeout(timer);
    }
  }, [overallDone, runningJobs.length]);

  const handleImport = async (urls: string[]) => {
    if (!token) return;
    try {
      await addPREntries(token, urls);
      loadData();
    } catch (e: unknown) {
      console.error('Import error:', e);
    }
  };

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
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink tracking-tight">Dashboard</h1>
          <p className="text-base text-muted mt-0.5">PR review console</p>
        </div>
        {reviews.length > 0 && (
          <div className="text-sm text-faint tabular-nums">
            {reviews.filter(r => r.published).length} published &middot; {reviews.filter(r => !r.published && r.status === 'done').length} drafts
          </div>
        )}
      </div>

      <PRInput onSubmit={handleAnalyze} onImport={handleImport} disabled={isRunning} />

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
