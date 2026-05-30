/* PR URL input form with multi-URL support */

import { useState } from 'react';

interface Props {
  onSubmit: (urls: string[], tool: string, depth: string, model?: string) => void;
  onImport: (urls: string[]) => void;
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

export default function PRInput({ onSubmit, onImport, disabled }: Props) {
  const [urlText, setUrlText] = useState('');
  const [tool, setTool] = useState('review');
  const [depth, setDepth] = useState('standard');
  const [model, setModel] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const urls = urlText
      .split(/[\n,]+/)
      .map(u => u.trim())
      .filter(u => u.includes('github.com') && u.includes('/pull/'));
    if (urls.length === 0) return;
    onSubmit(urls, tool, depth, model || undefined);
  };

  const handleImport = (e: React.FormEvent) => {
    e.preventDefault();
    const urls = urlText
      .split(/[\n,]+/)
      .map(u => u.trim())
      .filter(u => u.includes('github.com') && u.includes('/pull/'));
    if (urls.length === 0) return;
    onImport(urls);
    setUrlText('');
  };

  const parseUrls = () =>
    urlText
      .split(/[\n,]+/)
      .map(u => u.trim())
      .filter(u => u.includes('github.com') && u.includes('/pull/'));

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <h2 className="text-lg font-bold text-white">Start Analysis</h2>
      <textarea
        placeholder="Paste GitHub PR URLs (one per line, or comma-separated)&#10;https://github.com/owner/repo/pull/123&#10;https://github.com/owner/repo/pull/456"
        value={urlText}
        onChange={e => setUrlText(e.target.value)}
        className="input min-h-[100px] resize-y text-sm"
        disabled={disabled}
      />
      <div className="flex flex-wrap gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-surface-200/50 mb-1.5">Tool</label>
          <select value={tool} onChange={e => setTool(e.target.value)} className="input" disabled={disabled}>
            {TOOLS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-surface-200/50 mb-1.5">Depth</label>
          <select value={depth} onChange={e => setDepth(e.target.value)} className="input" disabled={disabled}>
            {DEPTHS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-surface-200/50 mb-1.5">Model (optional)</label>
          <input
            type="text" value={model} onChange={e => setModel(e.target.value)}
            placeholder="deepseek-v4-pro" className="input" disabled={disabled}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleImport}
          className="btn-ghost flex-1"
          disabled={disabled || !urlText.trim()}
        >
          📥 Import PRs
        </button>
        <button
          type="submit"
          className="btn-primary flex-1"
          disabled={disabled || !urlText.trim()}
        >
          {disabled ? 'Running...' : '⚡ Start Analysis'}
        </button>
      </div>
    </form>
  );
}
