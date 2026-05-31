/* Merge readiness score gauge */

interface Props {
  score: number;
  recommendation: string;
}

export default function ScoreGauge({ score, recommendation }: Props) {
  const color = score >= 80 ? 'var(--color-success)' : score >= 50 ? 'var(--color-warning)' : 'var(--color-error)';
  const circumference = 2 * Math.PI * 38;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex items-center gap-2.5">
      <div className="relative w-12 h-12 flex-shrink-0">
        <svg className="w-12 h-12 -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="38" fill="none" stroke="var(--color-border)" strokeWidth="9" />
          <circle
            cx="50" cy="50" r="38" fill="none" stroke={color} strokeWidth="9"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.22, 1, 0.36, 1)' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-semibold text-ink tabular-nums">{score}</span>
        </div>
      </div>
      <div>
        <p className="text-xs font-medium text-ink capitalize leading-snug">{recommendation.replace(/_/g, ' ')}</p>
        <p className="text-[11px] text-muted">Merge readiness</p>
      </div>
    </div>
  );
}
