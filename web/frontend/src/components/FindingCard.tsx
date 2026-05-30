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
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-surface-200/50 w-16">Confidence</span>
      <div className="flex-1 h-1.5 bg-surface-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-surface-200/70 w-8 text-right">{pct}%</span>
    </div>
  );
}

function detectLanguage(filePath: string): string {
  const ext = filePath.split('.').pop()?.toLowerCase();
  const map: Record<string, string> = { py: 'python', ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript', rs: 'rust', go: 'go', java: 'java', rb: 'ruby', cpp: 'cpp', c: 'c', h: 'c', css: 'css', html: 'html', json: 'json', yaml: 'yaml', yml: 'yaml', md: 'markdown', sql: 'sql' };
  return map[ext || ''] || 'plaintext';
}

export default function FindingCard({ finding, index, showFeedback, feedbackUI, onJumpToFile }: Props) {
  const lang = detectLanguage(finding.location.path);

  return (
    <div className="card space-y-3 animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <span className="text-xs text-surface-200/40 font-mono">#{index + 1}</span>
          <span className={getSeverityBadge(finding.severity)}>{finding.severity.toUpperCase()}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-surface-700 text-surface-200/80">{finding.category}</span>
        </div>
        <ConfidenceBar confidence={finding.confidence} />
      </div>

      <h4 className="font-semibold text-white text-base">{finding.title}</h4>
      <p className="text-sm text-surface-200/80 leading-relaxed">{finding.description}</p>

      <div className="text-xs font-mono text-surface-200/40 flex items-center gap-1 flex-wrap">
        📍{' '}
        {onJumpToFile ? (
          <button
            onClick={() => onJumpToFile(finding.location.path)}
            className="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors"
            title="Jump to file in Diff view"
          >
            {finding.location.path}:{finding.location.range.start.line}
          </button>
        ) : (
          <span>{finding.location.path}:{finding.location.range.start.line}</span>
        )}
      </div>

      {finding.suggestion?.current_code && (
        <CodeBlock code={finding.suggestion.current_code} label="❌ Current Code" language={lang} />
      )}
      {finding.suggestion?.suggested_code && (
        <CodeBlock code={finding.suggestion.suggested_code} label="✅ Suggested Fix" language={lang} />
      )}

      {showFeedback && feedbackUI}
    </div>
  );
}
