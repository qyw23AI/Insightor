/* Single finding display — dense header, chip file path */

import type { Finding } from '../types/urf';
import CodeBlock from './CodeBlock';

interface Props {
  finding: Finding;
  index: number;
  showFeedback?: boolean;
  feedbackUI?: React.ReactNode;
  onJumpToFile?: (filePath: string) => void;
}

const SEV_CLASS: Record<string, string> = {
  critical: 'badge-critical',
  high:     'badge-high',
  medium:   'badge-medium',
  low:      'badge-low',
  info:     'badge-info',
};

function lang(path: string) {
  const ext = path.split('.').pop()?.toLowerCase();
  const map: Record<string, string> = {
    py: 'python', ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    rs: 'rust', go: 'go', java: 'java', rb: 'ruby', cpp: 'cpp', c: 'c', h: 'c',
    css: 'css', html: 'html', json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown', sql: 'sql',
  };
  return map[ext ?? ''] ?? 'plaintext';
}

function ConfidencePip({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 80 ? 'var(--color-success)' : pct >= 50 ? 'var(--color-warning)' : 'var(--color-error)';
  return (
    <div className="flex items-center gap-1.5" title={`${pct}% confidence`}>
      <div className="w-16 h-1 rounded-full overflow-hidden" style={{ background: 'var(--color-surface-high)' }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-[11px] text-faint tabular-nums w-7 text-right">{pct}%</span>
    </div>
  );
}

export default function FindingCard({ finding, index, showFeedback, feedbackUI, onJumpToFile }: Props) {
  const language = lang(finding.location.path);
  const fileName = finding.location.path.split('/').pop() ?? finding.location.path;

  return (
    <div
      className="card space-y-2.5 animate-fade-in"
      style={{ animationDelay: `${Math.min(index * 35, 350)}ms`, animationFillMode: 'backwards' }}
    >
      {/* Header: index · severity · category · confidence — all one row */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-faint font-mono tabular-nums w-6 flex-shrink-0">
          {String(index + 1).padStart(2, '0')}
        </span>
        <span className={`badge ${SEV_CLASS[finding.severity] ?? 'badge-info'}`}>
          {finding.severity}
        </span>
        <span className="text-xs px-1.5 py-0.5 rounded text-muted tabular-nums"
          style={{ background: 'var(--color-surface-high)', fontSize: '0.6875rem' }}>
          {finding.category}
        </span>
        <div className="flex-1 min-w-0" />
        <ConfidencePip confidence={finding.confidence} />
      </div>

      {/* Title + description */}
      <h4 className="text-base font-semibold text-ink leading-snug">{finding.title}</h4>
      <p className="text-sm text-muted leading-relaxed">{finding.description}</p>

      {/* File path chip */}
      <div>
        {onJumpToFile ? (
          <button
            onClick={() => onJumpToFile(finding.location.path)}
            className="inline-flex items-center gap-1 text-xs font-mono text-accent hover:text-accent-hover transition-colors px-2 py-0.5 rounded"
            style={{ background: 'oklch(0.68 0.16 175 / 0.08)', border: '1px solid oklch(0.68 0.16 175 / 0.15)' }}
            title="Jump to file in Diff view"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            {fileName}:{finding.location.range.start.line}
          </button>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-mono text-faint px-2 py-0.5 rounded"
            style={{ background: 'var(--color-surface-high)' }}>
            {fileName}:{finding.location.range.start.line}
          </span>
        )}
      </div>

      {/* Code blocks */}
      {finding.suggestion?.current_code && (
        <CodeBlock code={finding.suggestion.current_code} label="Current code" language={language} />
      )}
      {finding.suggestion?.suggested_code && (
        <CodeBlock code={finding.suggestion.suggested_code} label="Suggested fix" language={language} />
      )}

      {showFeedback && feedbackUI}
    </div>
  );
}
