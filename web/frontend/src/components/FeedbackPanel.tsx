/* Feedback interaction for a single finding — status buttons + optional note */

import { useState } from 'react';
import type { Finding, FeedbackItem } from '../types/urf';

const STATUSES = [
  { value: 'confirmed', label: '✅ Confirmed', color: 'text-green-400' },
  { value: 'false_positive', label: '❌ False Positive', color: 'text-red-400' },
  { value: 'addressed', label: '🔧 Addressed', color: 'text-blue-400' },
  { value: 'ignored', label: '⏭️ Ignored', color: 'text-gray-400' },
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
    <div className="space-y-3 pt-3 border-t border-surface-700/50">
      <div className="flex flex-wrap gap-1.5">
        {STATUSES.map(s => (
          <button
            key={s.value}
            type="button"
            onClick={() => handleStatus(s.value)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all border ${
              status === s.value
                ? `${s.color} border-current bg-surface-700/50`
                : 'text-surface-200/50 border-surface-700 hover:border-surface-200/30'
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
