/* Single finding display card */

import type { Finding } from '../types/urf';
import CodeBlock from './CodeBlock';

interface Props {
  finding: Finding;
  index: number;
  showFeedback?: boolean;
  feedbackUI?: React.ReactNode;
  onJumpToFile?: (filePath: string) => void;
}

function getSeverityBadge(severity: string) {
  const map: Record<string, string> = {
    critical: 'badge-critical',
    high: 'badge-high',
    medium: 'badge-medium',
    low: 'badge-low',
    info: 'badge-info',
  };
  return map[severity] || 'badge-info';
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 80 ? 'bg-success' : pct >= 50 ? 'bg-warning' : 'bg-error';
  return (
    <div className="flex items-center gap-2 text-2xs">
      <span className="text-faint w-14">Confidence</span>
      <div className="flex-1 h-1 bg-app-surface-high rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-500 ease-out-expo`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-muted w-8 text-right tabular-nums">{pct}%</span>
    </div>
  );
}

function detectLanguage(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase();
  const map: Record<string, string> = {
    py: 'python', ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
    rs: 'rust', go: 'go', java: 'java', rb: 'ruby', cpp: 'cpp', c: 'c', h: 'c',
    css: 'css', html: 'html', json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown', sql: 'sql',
  };
  return map[ext || ''] || 'plaintext';
}

export default function FindingCard({ finding, index, showFeedback, feedbackUI, onJumpToFile }: Props) {
  const lang = detectLanguage(finding.location.path);

  return (
    <div className="card space-y-3 animate-fade-in" style={{ animationDelay: `${Math.min(index * 40, 400)}ms`, animationFillMode: 'backwards' }}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-2xs text-faint font-mono tabular-nums">#{index + 1}</span>
          <span className={getSeverityBadge(finding.severity)}>{finding.severity}</span>
          <span className="text-2xs px-2 py-0.5 rounded bg-app-surface-high text-muted">{finding.category}</span>
        </div>
        <ConfidenceBar confidence={finding.confidence} />
      </div>

      <h4 className="font-medium text-ink text-sm">{finding.title}</h4>
      <p className="text-xs text-muted leading-relaxed">{finding.description}</p>

      <div className="text-2xs font-mono text-faint flex items-center gap-1 flex-wrap">
        {onJumpToFile ? (
          <button
            onClick={() => onJumpToFile(finding.location.path)}
            className="text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
            title="Jump to file in Diff view"
          >
            {finding.location.path}:{finding.location.range.start.line}
          </button>
        ) : (
          <span>{finding.location.path}:{finding.location.range.start.line}</span>
        )}
      </div>

      {finding.suggestion?.current_code && (
        <CodeBlock code={finding.suggestion.current_code} label="Current code" language={lang} />
      )}
      {finding.suggestion?.suggested_code && (
        <CodeBlock code={finding.suggestion.suggested_code} label="Suggested fix" language={lang} />
      )}

      {showFeedback && feedbackUI}
    </div>
  );
}
