import { useMemo } from 'react';
import { NpcSummary } from '../types';

interface Props {
  npcs: NpcSummary[];
  loading?: boolean;
  onOpenChat: (slug: string) => void;
  onCreate: () => void;
}

function StatCardSkeleton() {
  return (
    <div className="animate-pulse rounded-lg border border-outline-variant bg-surface-container p-6">
      <div className="h-3 w-24 rounded bg-surface-container-highest" />
      <div className="mt-3 h-8 w-12 rounded bg-surface-container-highest" />
    </div>
  );
}

export default function Dashboard({ npcs, loading, onOpenChat, onCreate }: Props) {
  const llmBreakdown = useMemo(() => {
    const counts = new Map<string, number>();
    for (const npc of npcs) {
      counts.set(npc.llm, (counts.get(npc.llm) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [npcs]);
  const maxCount = llmBreakdown[0]?.[1] ?? 0;

  return (
    <div className="h-full overflow-y-auto custom-scrollbar bg-surface-container-lowest p-gutter">
      <div className="mb-8">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">Dashboard</h2>
        <p className="mt-1 text-on-surface-variant">Overview of your narrative intelligence roster.</p>
      </div>

      {loading ? (
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      ) : (
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-outline-variant bg-surface-container p-6 transition-transform hover:-translate-y-0.5">
            <div className="mb-4 flex items-start justify-between">
              <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">Total NPCs</p>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 shadow-[0_0_16px_-4px_rgba(206,192,236,0.5)]">
                <span className="material-symbols-outlined text-[18px] text-primary">smart_toy</span>
              </div>
            </div>
            <p className="font-headline-lg text-headline-lg text-on-surface">{npcs.length}</p>
          </div>
          <div className="rounded-xl border border-outline-variant bg-surface-container p-6 transition-transform hover:-translate-y-0.5">
            <div className="mb-4 flex items-start justify-between">
              <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">LLMs in use</p>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 shadow-[0_0_16px_-4px_rgba(206,192,236,0.5)]">
                <span className="material-symbols-outlined text-[18px] text-primary">memory</span>
              </div>
            </div>
            <p className="font-headline-lg text-headline-lg text-on-surface">{llmBreakdown.length}</p>
          </div>
          <div className="rounded-xl border border-outline-variant bg-surface-container p-6 transition-transform hover:-translate-y-0.5">
            <div className="mb-4 flex items-start justify-between">
              <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">Most used LLM</p>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 shadow-[0_0_16px_-4px_rgba(206,192,236,0.5)]">
                <span className="material-symbols-outlined text-[18px] text-primary">bolt</span>
              </div>
            </div>
            <p className="truncate font-code-md text-code-md text-on-surface">{llmBreakdown[0]?.[0] ?? '—'}</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="h-64 animate-pulse rounded-lg border border-outline-variant bg-surface-container" />
          <div className="h-64 animate-pulse rounded-lg border border-outline-variant bg-surface-container" />
        </div>
      ) : npcs.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-outline-variant bg-surface-container py-24 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-surface-container-high shadow-[0_0_40px_-10px_rgba(208,188,255,0.2)]">
            <span className="material-symbols-outlined text-4xl leading-none text-primary/60">smart_toy</span>
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
          <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container">
            <div className="border-b border-outline-variant px-6 py-4">
              <h3 className="font-headline-sm text-headline-sm text-on-surface">LLM breakdown</h3>
            </div>
            <div className="divide-y divide-outline-variant/30">
              {llmBreakdown.map(([llm, count]) => (
                <div key={llm} className="space-y-2 px-6 py-3">
                  <div className="flex items-center justify-between">
                    <span className="font-code-md text-code-md text-on-surface-variant">{llm}</span>
                    <span className="rounded-lg bg-surface-container-highest px-2 py-1 font-label-caps text-[10px] uppercase text-on-surface-variant">
                      {count} {count === 1 ? 'npc' : 'npcs'} · {Math.round((count / npcs.length) * 100)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-container-highest">
                    <div
                      className="h-full rounded-full bg-primary/60"
                      style={{ width: `${(count / maxCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container">
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
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
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
