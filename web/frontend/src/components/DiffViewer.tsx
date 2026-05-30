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

/**
 * Parse unified diff string into per-file sections.
 * Supports "diff --git a/... b/..." and "--- a/... / +++ b/..." headers.
 */
function parseDiff(diffText: string): FileDiff[] {
  const files: FileDiff[] = [];
  const lines = diffText.split('\n');
  let current: FileDiff | null = null;
  let currentLines: string[] = [];
  let headerLines: string[] = [];

  for (const line of lines) {
    // Detect new file section: "diff --git a/<path> b/<path>"
    const gitMatch = line.match(/^diff --git a\/(.+?) b\/(.+?)$/);
    if (gitMatch) {
      // Flush previous file
      if (current) {
        current.hunks = currentLines.join('\n');
        files.push(current);
      }
      const filename = gitMatch[2] || gitMatch[1];
      const addDel = currentLines.join('\n');
      let adds = 0, dels = 0;
      for (const l of currentLines) {
        if (l.startsWith('+') && !l.startsWith('+++')) adds++;
        if (l.startsWith('-') && !l.startsWith('---')) dels++;
      }

      current = { filename, header: '', hunks: '', additions: 0, deletions: 0 };
      currentLines = [];
      headerLines = [line];
      continue;
    }

    if (current) {
      // Collect header lines (--- a/..., +++ b/..., rename from/to, etc.)
      if (headerLines.length < 10 && (line.startsWith('--- a/') || line.startsWith('+++ b/') ||
          line.startsWith('rename from ') || line.startsWith('rename to ') ||
          line.startsWith('new file ') || line.startsWith('deleted file ') ||
          line.startsWith('index ') || line.startsWith('Binary files'))) {
        headerLines.push(line);
        continue;
      }
      // Record header once we hit the first hunk or content
      if (headerLines.length > 0) {
        current.header = headerLines.join('\n');
        headerLines = [];
      }
      currentLines.push(line);
    }
  }

  // Flush last file
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

/** Sanitize filename into a valid DOM id. */
function fileAnchorId(filename: string): string {
  return 'diff-' + filename.replace(/[^a-zA-Z0-9_-]/g, '-');
}

interface Props {
  diffText: string;
  /** Optional: scroll to a specific file on mount. */
  scrollToFile?: string | null;
  onScrollDone?: () => void;
}

export default function DiffViewer({ diffText, scrollToFile, onScrollDone }: Props) {
  const files = useMemo(() => parseDiff(diffText), [diffText]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  // Scroll to file anchor when scrollToFile changes
  useState(() => {
    if (scrollToFile) {
      const id = fileAnchorId(scrollToFile);
      // Delay to let DOM render
      requestAnimationFrame(() => {
        const el = document.getElementById(id);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Highlight briefly
          el.classList.add('ring-2', 'ring-blue-500/50');
          setTimeout(() => {
            el.classList.remove('ring-2', 'ring-blue-500/50');
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
    return <p className="text-center py-8 text-surface-200/50">No diff available for this review.</p>;
  }

  // Stats
  const totalAdds = files.reduce((s, f) => s + f.additions, 0);
  const totalDels = files.reduce((s, f) => s + f.deletions, 0);

  return (
    <div className="space-y-2">
      {/* Summary bar */}
      <div className="flex items-center gap-3 text-xs text-surface-200/50 mb-3 px-1">
        <span>{files.length} file{files.length > 1 ? 's' : ''}</span>
        <span className="text-green-400">+{totalAdds}</span>
        <span className="text-red-400">-{totalDels}</span>
        <button
          onClick={() => {
            if (collapsed.size === files.length) {
              setCollapsed(new Set());
            } else {
              setCollapsed(new Set(files.map(f => f.filename)));
            }
          }}
          className="ml-auto text-blue-400 hover:text-blue-300 transition-colors"
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
            className="border border-surface-700 rounded-lg overflow-hidden transition-all scroll-mt-20"
          >
            {/* File header — clickable to toggle */}
            <button
              onClick={() => toggleCollapse(file.filename)}
              className="w-full flex items-center gap-3 px-4 py-2.5 bg-surface-800 hover:bg-surface-700/80 transition-colors text-left"
            >
              <span className="text-xs text-surface-200/40">
                {isCollapsed ? '▶' : '▼'}
              </span>
              <code className="text-sm text-white flex-1 truncate">{file.filename}</code>
              <span className="text-xs text-green-400 font-mono">+{file.additions}</span>
              <span className="text-xs text-red-400 font-mono">-{file.deletions}</span>
            </button>

            {/* File content */}
            {!isCollapsed && (
              <div className="border-t border-surface-700">
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
