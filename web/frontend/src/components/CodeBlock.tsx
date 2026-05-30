/* Syntax-highlighted code block */

import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';

interface Props {
  code: string;
  label?: string;
  language?: string;
}

export default function CodeBlock({ code, label, language }: Props) {
  if (!code) return null;

  return (
    <div className="space-y-1.5">
      {label && <p className="text-xs font-medium text-surface-200/60">{label}</p>}
      <div className="rounded-lg overflow-hidden border border-surface-700">
        <SyntaxHighlighter
          language={language || 'python'}
          style={atomOneDark}
          customStyle={{
            margin: 0,
            padding: '12px 16px',
            background: '#0d1117',
            fontSize: '13px',
            borderRadius: '0',
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
