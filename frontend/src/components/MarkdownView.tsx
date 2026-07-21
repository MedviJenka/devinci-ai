import { Fragment, ReactNode } from 'react';

interface Props {
  content: string;
  className?: string;
}

const HEADER_COLORS = ['text-primary', 'text-tertiary', 'text-sky-400', 'text-emerald-400'];

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const regex = /(\*\*.+?\*\*|`.+?`|\*[^*]+?\*|_[^_]+?_)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;

  while ((match = regex.exec(text))) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${i++}`;

    if (token.startsWith('**')) {
      nodes.push(
        <strong key={key} className="font-semibold text-amber-300">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith('`')) {
      nodes.push(
        <code key={key} className="rounded bg-surface-container-highest px-1.5 py-0.5 font-code-md text-[12px] text-emerald-300">
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      nodes.push(
        <em key={key} className="text-sky-300">
          {token.slice(1, -1)}
        </em>,
      );
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export default function MarkdownView({ content, className = '' }: Props) {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];
  let headerCount = 0;

  const flushList = (key: string) => {
    if (listItems.length === 0) return;
    blocks.push(
      <ul key={key} className="ml-1 list-none space-y-1.5">
        {listItems.map((item, idx) => (
          <li key={idx} className="flex gap-2 text-on-surface">
            <span className="mt-0.5 text-tertiary">▸</span>
            <span>{renderInline(item, `${key}-li-${idx}`)}</span>
          </li>
        ))}
      </ul>,
    );
    listItems = [];
  };

  lines.forEach((rawLine, idx) => {
    const line = rawLine.trimEnd();
    const key = `b-${idx}`;

    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      flushList(`${key}-list`);
      blocks.push(<hr key={key} className="my-3 border-outline-variant" />);
      return;
    }

    const headerMatch = /^(#{1,4})\s+(.*)$/.exec(line);
    if (headerMatch) {
      flushList(`${key}-list`);
      const level = headerMatch[1].length;
      const color = HEADER_COLORS[headerCount % HEADER_COLORS.length];
      headerCount += 1;
      const sizeClass =
        level === 1
          ? 'text-headline-md font-headline-md mt-5 mb-2'
          : level === 2
            ? 'text-headline-sm font-headline-sm mt-4 mb-2'
            : 'text-base font-semibold mt-3 mb-1.5 uppercase tracking-wide text-[13px]';
      blocks.push(
        <div key={key} className={`${sizeClass} ${color}`}>
          {renderInline(headerMatch[2], key)}
        </div>,
      );
      return;
    }

    const listMatch = /^\s*[-*]\s+(.*)$/.exec(line);
    if (listMatch) {
      listItems.push(listMatch[1]);
      return;
    }

    const quoteMatch = /^\s*>\s?(.*)$/.exec(line);
    if (quoteMatch) {
      flushList(`${key}-list`);
      blocks.push(
        <blockquote key={key} className="my-2 border-l-2 border-tertiary/60 pl-3 italic text-on-surface-variant">
          {renderInline(quoteMatch[1], key)}
        </blockquote>,
      );
      return;
    }

    if (line.trim() === '') {
      flushList(`${key}-list`);
      return;
    }

    flushList(`${key}-list`);
    blocks.push(
      <p key={key} className="leading-relaxed text-on-surface">
        {renderInline(line, key)}
      </p>,
    );
  });
  flushList('final-list');

  return (
    <div className={`space-y-1.5 font-body-md text-body-md ${className}`}>
      {blocks.map((block, idx) => (
        <Fragment key={idx}>{block}</Fragment>
      ))}
    </div>
  );
}
