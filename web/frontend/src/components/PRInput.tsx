/* PR URL input — command-bar style with segmented controls */

import { useState } from 'react';

interface Props {
  onSubmit: (urls: string[], tool: string, depth: string, model?: string) => void;
  onImport: (urls: string[]) => void;
  disabled?: boolean;
}

const TOOLS  = [{ value: 'review', label: 'Review' }, { value: 'describe', label: 'Describe' }, { value: 'risks', label: 'Risks' }];
const DEPTHS = [{ value: 'quick', label: 'Quick' }, { value: 'standard', label: 'Standard' }, { value: 'deep', label: 'Deep' }];

function SegControl({
  options,
  value,
  onChange,
  disabled,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
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

export default function PRInput({ onSubmit, onImport, disabled }: Props) {
  const [urlText, setUrlText]   = useState('');
  const [tool, setTool]         = useState('review');
  const [depth, setDepth]       = useState('standard');
  const [model, setModel]       = useState('');

  const parseUrls = () =>
    urlText.split(/[\n,]+/).map(u => u.trim())
      .filter(u => u.includes('github.com') && u.includes('/pull/'));

  const urlCount = parseUrls().length;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const urls = parseUrls();
    if (urls.length === 0) return;
    onSubmit(urls, tool, depth, model || undefined);
  };

  const handleImport = () => {
    const urls = parseUrls();
    if (urls.length === 0) return;
    onImport(urls);
    setUrlText('');
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">New analysis</h2>
        {urlCount > 0 && (
          <span className="text-xs text-muted tabular-nums">{urlCount} PR{urlCount !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* URL textarea */}
      <textarea
        placeholder={`Paste GitHub PR URLs — one per line\nhttps://github.com/owner/repo/pull/123`}
        value={urlText}
        onChange={e => setUrlText(e.target.value)}
        className="input font-mono text-xs resize-none"
        style={{ minHeight: 72, lineHeight: 1.6 }}
        disabled={disabled}
      />

      {/* Controls row */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <p className="text-xs text-faint">Tool</p>
          <SegControl options={TOOLS} value={tool} onChange={setTool} disabled={disabled} />
        </div>
        <div className="space-y-1">
          <p className="text-xs text-faint">Depth</p>
          <SegControl options={DEPTHS} value={depth} onChange={setDepth} disabled={disabled} />
        </div>
        <div className="flex-1 min-w-[148px] space-y-1">
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

      {/* Actions */}
      <div className="flex gap-2 pt-0.5">
        <button
          type="button"
          onClick={handleImport}
          className="btn-secondary btn-sm flex-1"
          disabled={disabled || urlCount === 0}
        >
          Import PRs
        </button>
        <button
          type="submit"
          className="btn-primary btn-sm flex-1"
          disabled={disabled || urlCount === 0}
        >
          {disabled ? 'Running...' : 'Start analysis'}
        </button>
      </div>
    </form>
  );
}
