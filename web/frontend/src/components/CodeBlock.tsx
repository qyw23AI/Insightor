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
      {label && (
        <p className="text-2xs font-medium text-faint">{label}</p>
      )}
      <div className="rounded-md overflow-hidden border border-border">
        <SyntaxHighlighter
          language={language || 'python'}
          style={atomOneDark}
          customStyle={{
            margin: 0,
            padding: '12px 16px',
            background: 'oklch(0.11 0.003 268)',
            fontSize: '13px',
            borderRadius: '0',
            lineHeight: '1.6',
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
