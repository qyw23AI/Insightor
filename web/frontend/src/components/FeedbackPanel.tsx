/* Feedback interaction for a single finding */

import { useState } from 'react';
import type { Finding, FeedbackItem } from '../types/urf';

const STATUSES = [
  { value: 'confirmed', label: 'Confirmed', activeClass: 'text-success border-success/30 bg-success/8' },
  { value: 'false_positive', label: 'False positive', activeClass: 'text-error border-error/30 bg-error/8' },
  { value: 'addressed', label: 'Addressed', activeClass: 'text-accent border-accent/30 bg-accent/8' },
  { value: 'ignored', label: 'Ignored', activeClass: 'text-muted border-border-hover bg-app-surface-elevated' },
];

interface Props {
  finding: Finding;
  onChange: (item: FeedbackItem) => void;
  initial?: FeedbackItem | null;
}

export default function FeedbackPanel({ finding, onChange, initial }: Props) {
  const [status, setStatus] = useState(initial?.status || '');
  const [note, setNote] = useState(initial?.note || '');

  const handleStatus = (s: string) => {
    const newStatus = status === s ? '' : s;
    setStatus(newStatus);
    onChange({ finding_id: finding.id, status: newStatus, note, reviewer: null });
  };

  const handleNote = (val: string) => {
    setNote(val);
    onChange({ finding_id: finding.id, status, note: val, reviewer: null });
  };

  return (
    <div className="space-y-3 pt-3 border-t border-border">
      <p className="text-xs text-faint font-medium">Mark this finding</p>
      <div className="flex flex-wrap gap-1.5">
        {STATUSES.map(s => (
          <button
            key={s.value}
            type="button"
            onClick={() => handleStatus(s.value)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-150 border active:scale-95 ${
              status === s.value
                ? s.activeClass
                : 'text-muted border-border hover:border-border-hover hover:text-ink'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      {status && (
        <input
          type="text"
          placeholder="Add an optional note..."
          value={note}
          onChange={e => handleNote(e.target.value)}
          className="input text-sm w-full"
        />
      )}
    </div>
  );
}
