/* Recent PR entries list with multi-select and batch review controls */

import { useState } from 'react';
import type { PREntry } from '../types/urf';

interface Props {
  entries: PREntry[];
  onBatchReview: (urls: string[], tool: string, depth: string, model?: string) => void;
  onDelete?: (id: string) => void;
  disabled?: boolean;
}

const TOOLS = [
  { value: 'review', label: 'Review' },
  { value: 'describe', label: 'Describe' },
  { value: 'risks', label: 'Risks' },
];

const DEPTHS = [
  { value: 'quick', label: 'Quick' },
  { value: 'standard', label: 'Standard' },
  { value: 'deep', label: 'Deep' },
];

export default function PREntryList({ entries, onBatchReview, onDelete, disabled }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [tool, setTool] = useState('review');
  const [depth, setDepth] = useState('standard');
  const [model, setModel] = useState('');

  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const toggleAll = () => {
    if (selected.size === entries.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(entries.map(e => e.id)));
    }
  };

  const handleBatch = () => {
    const urls = entries.filter(e => selected.has(e.id)).map(e => e.pr_url);
    if (urls.length === 0) return;
    onBatchReview(urls, tool, depth, model || undefined);
    setSelected(new Set());
  };

  if (entries.length === 0) return null;

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">Recent PRs ({entries.length})</h3>
        <button onClick={toggleAll} className="btn-ghost btn-sm text-xs">
          {selected.size === entries.length ? 'Deselect all' : 'Select all'}
        </button>
      </div>

      <div className="space-y-1 max-h-48 overflow-y-auto">
        {entries.map(e => (
          <div
            key={e.id}
            className={`flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-all duration-150 ${
              selected.has(e.id)
                ? 'bg-primary/6 border border-primary/20'
                : 'hover:bg-app-surface-elevated border border-transparent'
            }`}
          >
            <input
              type="checkbox"
              checked={selected.has(e.id)}
              onChange={() => toggle(e.id)}
              className="checkbox"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-ink truncate">{e.repo}#{e.pr_number}</p>
              <p className="text-2xs text-faint truncate font-mono">{e.pr_url}</p>
            </div>
            <span className={`badge text-2xs ${
              e.status === 'done' ? 'badge-success' :
              e.status === 'running' ? 'badge-info' :
              'badge-low'
            }`}>
              {e.status}
            </span>
            {onDelete && (
              <button
                onClick={() => onDelete(e.id)}
                className="text-faint hover:text-error transition-colors p-1"
                title="Delete entry"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Batch review controls */}
      {selected.size > 0 && (
        <div className="pt-3 border-t border-border space-y-3">
          <div className="flex flex-wrap gap-3">
            <div className="flex-1 min-w-[120px]">
              <label className="block text-xs font-medium text-muted mb-1">Tool</label>
              <select value={tool} onChange={e => setTool(e.target.value)} className="input text-sm" disabled={disabled}>
                {TOOLS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[120px]">
              <label className="block text-xs font-medium text-muted mb-1">Depth</label>
              <select value={depth} onChange={e => setDepth(e.target.value)} className="input text-sm" disabled={disabled}>
                {DEPTHS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[150px]">
              <label className="block text-xs font-medium text-muted mb-1">Model (optional)</label>
              <input
                type="text" value={model} onChange={e => setModel(e.target.value)}
                placeholder="deepseek-v4-pro" className="input text-sm font-mono" disabled={disabled}
              />
            </div>
          </div>
          <button
            onClick={handleBatch}
            disabled={disabled}
            className="btn-primary w-full text-sm"
          >
            Review selected ({selected.size})
          </button>
        </div>
      )}
    </div>
  );
}
