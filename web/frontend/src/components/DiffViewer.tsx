/* File-separated diff viewer with collapsible sections */

import { useMemo, useState } from 'react';
import CodeBlock from './CodeBlock';

interface FileDiff {
  filename: string;
  header: string;
  hunks: string;
  additions: number;
  deletions: number;
}

function parseDiff(diffText: string): FileDiff[] {
  const files: FileDiff[] = [];
  const lines = diffText.split('\n');
  let current: FileDiff | null = null;
  let currentLines: string[] = [];
  let headerLines: string[] = [];

  for (const line of lines) {
    const gitMatch = line.match(/^diff --git a\/(.+?) b\/(.+?)$/);
    if (gitMatch) {
      if (current) {
        current.hunks = currentLines.join('\n');
        files.push(current);
      }
      const filename = gitMatch[2] || gitMatch[1];
      current = { filename, header: '', hunks: '', additions: 0, deletions: 0 };
      currentLines = [];
      headerLines = [line];
      continue;
    }

    if (current) {
      if (headerLines.length < 10 && (line.startsWith('--- a/') || line.startsWith('+++ b/') ||
          line.startsWith('rename from ') || line.startsWith('rename to ') ||
          line.startsWith('new file ') || line.startsWith('deleted file ') ||
          line.startsWith('index ') || line.startsWith('Binary files'))) {
        headerLines.push(line);
        continue;
      }
      if (headerLines.length > 0) {
        current.header = headerLines.join('\n');
        headerLines = [];
      }
      currentLines.push(line);
    }
  }

  if (current) {
    let adds = 0, dels = 0;
    for (const l of currentLines) {
      if (l.startsWith('+') && !l.startsWith('+++')) adds++;
      if (l.startsWith('-') && !l.startsWith('---')) dels++;
    }
    current.hunks = currentLines.join('\n');
    current.additions = adds;
    current.deletions = dels;
    files.push(current);
  }

  return files;
}

function fileAnchorId(filename: string): string {
  return 'diff-' + filename.replace(/[^a-zA-Z0-9_-]/g, '-');
}

interface Props {
  diffText: string;
  scrollToFile?: string | null;
  onScrollDone?: () => void;
}

export default function DiffViewer({ diffText, scrollToFile, onScrollDone }: Props) {
  const files = useMemo(() => parseDiff(diffText), [diffText]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  useState(() => {
    if (scrollToFile) {
      const id = fileAnchorId(scrollToFile);
      requestAnimationFrame(() => {
        const el = document.getElementById(id);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          el.classList.add('ring-spot');
          setTimeout(() => {
            el.classList.remove('ring-spot');
            onScrollDone?.();
          }, 2000);
        }
      });
    }
  });

  const toggleCollapse = (filename: string) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      next.has(filename) ? next.delete(filename) : next.add(filename);
      return next;
    });
  };

  if (files.length === 0) {
    return <p className="text-center py-8 text-muted">No diff available for this review.</p>;
  }

  const totalAdds = files.reduce((s, f) => s + f.additions, 0);
  const totalDels = files.reduce((s, f) => s + f.deletions, 0);

  return (
    <div className="space-y-1.5">
      {/* Summary bar */}
      <div className="flex items-center gap-3 text-2xs text-faint mb-3 px-1">
        <span>{files.length} file{files.length > 1 ? 's' : ''}</span>
        <span className="text-success tabular-nums">+{totalAdds}</span>
        <span className="text-error tabular-nums">-{totalDels}</span>
        <button
          onClick={() => {
            if (collapsed.size === files.length) {
              setCollapsed(new Set());
            } else {
              setCollapsed(new Set(files.map(f => f.filename)));
            }
          }}
          className="ml-auto text-accent hover:text-accent-hover transition-colors"
        >
          {collapsed.size === files.length ? 'Expand all' : 'Collapse all'}
        </button>
      </div>

      {files.map((file, i) => {
        const cid = fileAnchorId(file.filename);
        const isCollapsed = collapsed.has(file.filename);

        return (
          <div
            key={i}
            id={cid}
            className="border border-border rounded-md overflow-hidden transition-all scroll-mt-20"
          >
            {/* File header */}
            <button
              onClick={() => toggleCollapse(file.filename)}
              className="w-full flex items-center gap-3 px-4 py-2.5 bg-app-surface hover:bg-app-surface-elevated transition-colors text-left"
            >
              <svg
                width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                className={`text-faint transition-transform duration-200 ${isCollapsed ? '' : 'rotate-90'}`}
              >
                <polyline points="9 18 15 12 9 6" />
              </svg>
              <code className="text-xs text-ink flex-1 truncate">{file.filename}</code>
              <span className="text-2xs text-success font-mono tabular-nums">+{file.additions}</span>
              <span className="text-2xs text-error font-mono tabular-nums">-{file.deletions}</span>
            </button>

            {/* File content */}
            {!isCollapsed && (
              <div className="border-t border-border">
                <CodeBlock code={(file.header ? file.header + '\n' : '') + file.hunks} language="diff" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export { fileAnchorId };
