/* URF TypeScript types — mirror of insightor/schemas/urf.py */

export interface ReviewResult {
  meta: ReviewMeta;
  summary: PRSummary;
  file_walkthrough: FileWalkthrough[];
  findings: Finding[];
  stats: ReviewStats;
  merge_readiness: MergeReadiness | null;
  context_summary: ContextSummary | null;
}

export interface ReviewMeta {
  pr_url: string;
  commit_sha: string;
  analysis_depth: string;
  model: string;
  timestamp: string;
  duration_ms: number;
  tokens_used: number;
  files_analyzed: number;
  files_skipped: number;
  is_incremental: boolean;
  base_review_id: string | null;
  new_findings_count: number;
  resolved_findings_count: number;
  reconfirmed_findings_count: number;
  context_layers: string[];
}

export interface PRSummary {
  pr_type: string;
  overview: string;
  files_changed: number;
  additions: number;
  deletions: number;
  diagram: string;
}

export interface FileWalkthrough {
  path: string;
  edit_type: 'added' | 'modified' | 'deleted' | 'renamed';
  summary: string;
  risk_count: number;
  suggestion_count: number;
}

export interface Finding {
  id: string;
  type: 'risk' | 'suggestion' | 'observation';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  title: string;
  description: string;
  location: {
    path: string;
    range: {
      start: { line: number; column: number };
      end: { line: number; column: number };
    };
  };
  suggestion: {
    current_code: string;
    suggested_code: string;
    is_committable: boolean;
  } | null;
  confidence: number;
  fingerprint: string;
  feedback: {
    status: 'confirmed' | 'false_positive' | 'addressed' | 'ignored' | null;
    reviewer_note: string | null;
    reviewed_by: string | null;
    reviewed_at: string | null;
  } | null;
}

export interface ReviewStats {
  total_findings: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  incremental: {
    new: number;
    resolved: number;
    reconfirmed: number;
    obsolete: number;
  } | null;
  quality: QualityMetrics | null;
}

export interface QualityMetrics {
  confidence_distribution: Record<string, number>;
  self_reflection_avg_score: number | null;
  historical_precision: Record<string, number>;
  test_files_in_diff: number;
}

export interface MergeReadiness {
  score: number;
  recommendation: 'safe_to_merge' | 'needs_review' | 'needs_work' | 'blocked';
  blocking_issues: string[];
  review_priority: 'low' | 'medium' | 'high';
  estimated_review_time_min: number;
  summary: string;
}

export interface ContextSummary {
  layers_used: string[];
  related_files_analyzed: string[];
  issues_referenced: string[];
  tokens_by_layer: Record<string, number>;
}

export interface JobInfo {
  job_id: string;
  pr_url: string;
  pr_number: number;
}

export interface ReviewSummary {
  id: string;
  pr_entry_id: string;
  pr_url: string;
  pr_number: number;
  job_id: string;
  tool: string;
  depth: string;
  status: string;
  published: boolean;
  findings_count: number;
  score: number | null;
  duration_ms: number;
  tokens_used: number;
  created_at: string | null;
  completed_at: string | null;
}

export interface PREntry {
  id: string;
  pr_url: string;
  pr_number: number;
  repo: string;
  title: string;
  status: string;
  added_at: string | null;
  last_reviewed_at: string | null;
}

export interface UserInfo {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string | null;
  last_login: string | null;
}

export interface FeedbackItem {
  finding_id: string;
  status: string;
  note: string | null;
  reviewer: string | null;
}
