/* Recent PR entries — multi-select + batch review with segmented controls */

import { useState } from 'react';
import type { PREntry } from '../types/urf';

interface Props {
  entries: PREntry[];
  onBatchReview: (urls: string[], tool: string, depth: string, model?: string) => void;
  onDelete?: (id: string) => void;
  disabled?: boolean;
}

const TOOLS  = [{ value: 'review', label: 'Review' }, { value: 'describe', label: 'Describe' }, { value: 'risks', label: 'Risks' }];
const DEPTHS = [{ value: 'quick', label: 'Quick' }, { value: 'standard', label: 'Standard' }, { value: 'deep', label: 'Deep' }];

function SegControl({
  options, value, onChange, disabled,
}: { options: { value: string; label: string }[]; value: string; onChange: (v: string) => void; disabled?: boolean }) {
  return (
    <div className="seg-control">
      {options.map(opt => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          disabled={disabled}
          className={`seg-btn${value === opt.value ? ' active' : ''}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export default function PREntryList({ entries, onBatchReview, onDelete, disabled }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [tool, setTool]         = useState('review');
  const [depth, setDepth]       = useState('standard');
  const [model, setModel]       = useState('');

  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const toggleAll = () => {
    setSelected(selected.size === entries.length ? new Set() : new Set(entries.map(e => e.id)));
  };

  const handleBatch = () => {
    const urls = entries.filter(e => selected.has(e.id)).map(e => e.pr_url);
    if (urls.length === 0) return;
    onBatchReview(urls, tool, depth, model || undefined);
    setSelected(new Set());
  };

  if (entries.length === 0) return null;

  const allSelected = selected.size === entries.length;

  return (
    <div className="card space-y-2.5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">
          Recent PRs
          <span className="text-faint font-normal ml-1.5">({entries.length})</span>
        </h3>
        <button onClick={toggleAll} className="btn-ghost btn-sm text-xs">
          {allSelected ? 'Deselect all' : 'Select all'}
        </button>
      </div>

      {/* Entry rows */}
      <div className="space-y-0.5 max-h-52 overflow-y-auto -mx-1 px-1">
        {entries.map(e => (
          <div
            key={e.id}
            onClick={() => toggle(e.id)}
            className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-md cursor-pointer transition-all duration-100 ${
              selected.has(e.id)
                ? 'bg-primary/6 border border-primary/20'
                : 'hover:bg-app-surface-elevated border border-transparent'
            }`}
          >
            <input
              type="checkbox"
              checked={selected.has(e.id)}
              onChange={() => toggle(e.id)}
              onClick={ev => ev.stopPropagation()}
              className="checkbox"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-ink truncate leading-snug font-mono">
                {e.repo}#{e.pr_number}
              </p>
              {e.title && (
                <p className="text-xs text-faint truncate leading-snug">{e.title}</p>
              )}
            </div>
            <span className={`badge ${
              e.status === 'done' ? 'badge-success' :
              e.status === 'running' ? 'badge-info' : 'badge-low'
            }`}>
              {e.status}
            </span>
            {onDelete && (
              <button
                onClick={ev => { ev.stopPropagation(); onDelete(e.id); }}
                className="icon-btn danger flex-shrink-0"
                title="Remove"
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Batch controls — only when items selected */}
      {selected.size > 0 && (
        <div className="pt-2.5 border-t border-border space-y-3 animate-fade-in">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <p className="text-xs text-faint">Tool</p>
              <SegControl options={TOOLS} value={tool} onChange={setTool} disabled={disabled} />
            </div>
            <div className="space-y-1">
              <p className="text-xs text-faint">Depth</p>
              <SegControl options={DEPTHS} value={depth} onChange={setDepth} disabled={disabled} />
            </div>
            <div className="flex-1 min-w-[140px] space-y-1">
              <p className="text-xs text-faint">Model <span className="text-faint/60">(optional)</span></p>
              <input
                type="text"
                value={model}
                onChange={e => setModel(e.target.value)}
                placeholder="deepseek-v4-pro"
                className="input font-mono text-xs"
                disabled={disabled}
              />
            </div>
          </div>
          <button onClick={handleBatch} disabled={disabled} className="btn-primary btn-sm w-full">
            Review {selected.size} selected PR{selected.size !== 1 ? 's' : ''}
          </button>
        </div>
      )}
    </div>
  );
}
