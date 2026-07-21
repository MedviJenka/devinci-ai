import { useMemo } from 'react';
import { NpcSummary } from '../types';

interface Props {
  npcs: NpcSummary[];
  onOpenChat: (slug: string) => void;
  onCreate: () => void;
}

export default function Dashboard({ npcs, onOpenChat, onCreate }: Props) {
  const llmBreakdown = useMemo(() => {
    const counts = new Map<string, number>();
    for (const npc of npcs) {
      counts.set(npc.llm, (counts.get(npc.llm) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [npcs]);

  return (
    <div className="h-full overflow-y-auto custom-scrollbar bg-surface-container-lowest p-gutter">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">Dashboard</h2>
          <p className="mt-1 text-on-surface-variant">Overview of your narrative intelligence roster.</p>
        </div>
        <button
          onClick={onCreate}
          className="flex shrink-0 items-center gap-2 rounded-lg bg-primary px-4 py-2.5 font-label-caps text-label-caps uppercase text-on-primary shadow-lg shadow-primary/10 transition-all hover:brightness-110 active:scale-[0.98]"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          New NPC
        </button>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-outline-variant bg-surface-container p-6">
          <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">Total NPCs</p>
          <p className="mt-2 font-headline-lg text-headline-lg text-on-surface">{npcs.length}</p>
        </div>
        <div className="rounded-lg border border-outline-variant bg-surface-container p-6">
          <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">LLMs in use</p>
          <p className="mt-2 font-headline-lg text-headline-lg text-on-surface">{llmBreakdown.length}</p>
        </div>
        <div className="rounded-lg border border-outline-variant bg-surface-container p-6">
          <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">Most used LLM</p>
          <p className="mt-2 truncate font-code-md text-code-md text-on-surface">{llmBreakdown[0]?.[0] ?? '—'}</p>
        </div>
      </div>

      {npcs.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-outline-variant bg-surface-container py-24 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-surface-container-high shadow-[0_0_40px_-10px_rgba(208,188,255,0.2)]">
            <span className="material-symbols-outlined text-4xl text-primary/60">smart_toy</span>
          </div>
          <h3 className="mb-2 font-headline-md text-headline-md text-on-surface">The Archive is Silent</h3>
          <p className="mx-auto mb-8 max-w-md text-on-surface-variant">
            No entities were found. Ready to forge your first narrative intelligence?
          </p>
          <button
            onClick={onCreate}
            className="rounded-lg bg-primary px-8 py-3 font-label-caps text-label-caps uppercase text-on-primary shadow-lg shadow-primary/10 transition-all hover:brightness-110"
          >
            Create First NPC
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container">
            <div className="border-b border-outline-variant px-6 py-4">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">LLM breakdown</h3>
            </div>
            <div className="divide-y divide-outline-variant/30">
              {llmBreakdown.map(([llm, count]) => (
                <div key={llm} className="flex items-center justify-between px-6 py-3">
                  <span className="font-code-md text-code-md text-on-surface-variant">{llm}</span>
                  <span className="rounded-lg bg-surface-container-highest px-2 py-1 font-label-caps text-[10px] uppercase text-on-surface-variant">
                    {count} {count === 1 ? 'npc' : 'npcs'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-outline-variant bg-surface-container">
            <div className="border-b border-outline-variant px-6 py-4">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">Roster</h3>
            </div>
            <div className="divide-y divide-outline-variant/30">
              {npcs.map((npc) => (
                <button
                  key={npc.slug}
                  onClick={() => onOpenChat(npc.slug)}
                  className="flex w-full items-center gap-3 px-6 py-3 text-left transition-colors hover:bg-primary/5"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-outline-variant bg-surface-container-highest">
                    <span className="material-symbols-outlined text-sm text-primary">smart_toy</span>
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-on-surface">{npc.role}</p>
                    <p className="truncate text-xs text-outline">{npc.goal}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
