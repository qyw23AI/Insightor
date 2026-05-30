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
  { value: 'review', label: '🔍 Review' },
  { value: 'describe', label: '📝 Describe' },
  { value: 'risks', label: '⚠️ Risks' },
];

const DEPTHS = [
  { value: 'quick', label: '⚡ Quick' },
  { value: 'standard', label: '📐 Standard' },
  { value: 'deep', label: '🔬 Deep' },
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
        <h3 className="font-semibold text-white">Recent PRs ({entries.length})</h3>
        <div className="flex gap-2">
          <button onClick={toggleAll} className="btn-ghost text-xs">
            {selected.size === entries.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>
      </div>

      <div className="space-y-1 max-h-48 overflow-y-auto">
        {entries.map(e => (
          <div
            key={e.id}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
              selected.has(e.id) ? 'bg-blue-600/10 border border-blue-500/30' : 'hover:bg-surface-700/50'
            }`}
          >
            <input
              type="checkbox"
              checked={selected.has(e.id)}
              onChange={() => toggle(e.id)}
              className="w-4 h-4 rounded accent-blue-500"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white truncate">{e.repo}#{e.pr_number}</p>
              <p className="text-xs text-surface-200/50 truncate">{e.pr_url}</p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${
              e.status === 'done' ? 'bg-green-500/20 text-green-400' :
              e.status === 'running' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-surface-700 text-surface-200/50'
            }`}>
              {e.status}
            </span>
            {onDelete && (
              <button onClick={() => onDelete(e.id)} className="text-xs text-red-400/50 hover:text-red-400">✕</button>
            )}
          </div>
        ))}
      </div>

      {/* Batch review controls */}
      {selected.size > 0 && (
        <div className="pt-3 border-t border-surface-700 space-y-3">
          <div className="flex flex-wrap gap-3">
            <div className="flex-1 min-w-[120px]">
              <label className="block text-xs font-medium text-surface-200/50 mb-1">Tool</label>
              <select value={tool} onChange={e => setTool(e.target.value)} className="input text-sm" disabled={disabled}>
                {TOOLS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[120px]">
              <label className="block text-xs font-medium text-surface-200/50 mb-1">Depth</label>
              <select value={depth} onChange={e => setDepth(e.target.value)} className="input text-sm" disabled={disabled}>
                {DEPTHS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-[150px]">
              <label className="block text-xs font-medium text-surface-200/50 mb-1">Model (optional)</label>
              <input
                type="text" value={model} onChange={e => setModel(e.target.value)}
                placeholder="deepseek-v4-pro" className="input text-sm" disabled={disabled}
              />
            </div>
          </div>
          <button
            onClick={handleBatch}
            disabled={disabled}
            className="btn-primary w-full text-sm"
          >
            ⚡ Review Selected ({selected.size})
          </button>
        </div>
      )}
    </div>
  );
}
