import { useEffect, useMemo, useRef, useState } from 'react';
import { NpcSummary } from '../types';

interface Props {
  npcs: NpcSummary[];
  onOpenChat: (slug: string) => void;
  onOpenPersona: (slug: string) => void;
  onDelete: (slug: string) => void;
  onCreate: () => void;
  onNavigateStorylines?: () => void;
}

const METRIC_BAR_HEIGHTS = [30, 45, 20, 60, 85, 40, 55, 70, 35, 90, 50, 65];

export default function Library({ npcs, onOpenChat, onOpenPersona, onDelete, onCreate, onNavigateStorylines }: Props) {
  const [query, setQuery] = useState('');
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== '/') return;
      const target = e.target as HTMLElement | null;
      const isTyping = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
      if (isTyping) return;
      e.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return npcs;
    return npcs.filter((n) => n.role.toLowerCase().includes(q) || n.slug.toLowerCase().includes(q) || n.goal.toLowerCase().includes(q));
  }, [npcs, query]);

  return (
    <div className="h-full overflow-y-auto custom-scrollbar bg-surface-container-lowest p-gutter">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">Entity Library</h2>
          <p className="mt-1 text-on-surface-variant">Manage your narrative intelligence components.</p>
        </div>
        <div className="relative w-72">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-on-surface-variant">
            search
          </span>
          <input
            ref={searchRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search NPC library..."
            className="w-full rounded-lg border border-outline-variant bg-surface-container py-1.5 pl-10 pr-10 text-body-md text-on-surface outline-none transition-all focus:ring-1 focus:ring-primary"
          />
          {!query && (
            <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-outline-variant bg-surface-container-high px-1.5 py-0.5 font-code-md text-[10px] text-on-surface-variant">
              /
            </kbd>
          )}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container shadow-2xl">
        {filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-high/50">
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Name</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">ID</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Status</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Last Called</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Call Count</th>
                  <th className="px-6 py-4 text-right font-label-caps uppercase tracking-wider text-on-surface-variant">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30">
                {filtered.map((npc) => (
                  <tr
                    key={npc.slug}
                    onClick={() => onOpenChat(npc.slug)}
                    className="group cursor-pointer transition-colors hover:bg-primary/5"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded border border-outline-variant bg-surface-container-highest">
                          <span className="material-symbols-outlined text-sm text-primary">smart_toy</span>
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-medium text-on-surface">{npc.role}</p>
                          <p className="truncate text-xs text-outline">{npc.goal}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="rounded bg-surface-container-lowest px-2 py-1 font-code-md text-code-md text-on-surface-variant">
                        {npc.slug}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                        <span className="font-label-caps text-xs uppercase text-primary">Published</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-on-surface-variant">—</td>
                    <td className="px-6 py-4 font-code-md text-on-surface-variant">—</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenPersona(npc.slug);
                          }}
                          title="Edit persona"
                          className="rounded p-2 text-on-surface-variant transition-all hover:bg-surface-container-highest hover:text-primary"
                        >
                          <span className="material-symbols-outlined text-lg">edit</span>
                        </button>
                        <button
                          onClick={(e) => e.stopPropagation()}
                          disabled
                          title="Analytics — coming soon"
                          className="cursor-not-allowed rounded p-2 text-on-surface-variant/40"
                        >
                          <span className="material-symbols-outlined text-lg">analytics</span>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(npc.slug);
                          }}
                          title="Delete NPC"
                          className="rounded p-2 text-on-surface-variant transition-all hover:bg-surface-container-highest hover:text-error"
                        >
                          <span className="material-symbols-outlined text-lg">delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="relative flex flex-col items-center justify-center overflow-hidden py-32 text-center">
            <div className="relative z-10">
              <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-surface-container-high shadow-[0_0_40px_-10px_rgba(208,188,255,0.2)]">
                <span className="material-symbols-outlined text-4xl text-primary/60">smart_toy</span>
              </div>
              <h3 className="mb-2 font-headline-md text-headline-md text-on-surface">
                {npcs.length === 0 ? 'The Archive is Silent' : 'No matches found'}
              </h3>
              <p className="mx-auto mb-8 max-w-md text-on-surface-variant">
                {npcs.length === 0
                  ? 'No entities were found. Ready to forge your first narrative intelligence?'
                  : 'No NPCs match your current search.'}
              </p>
              {npcs.length === 0 && (
                <button
                  onClick={onCreate}
                  className="rounded-lg bg-primary px-8 py-3 font-label-caps text-label-caps uppercase text-on-primary shadow-lg shadow-primary/10 transition-all hover:brightness-110"
                >
                  Create First NPC
                </button>
              )}
            </div>
          </div>
        )}
        {filtered.length > 0 && (
          <div className="flex items-center justify-between border-t border-outline-variant bg-surface-container-high/30 px-6 py-4">
            <span className="font-label-caps text-xs uppercase text-on-surface-variant">
              Showing {filtered.length} of {npcs.length} NPCs
            </span>
            <div className="flex gap-2">
              <button
                disabled
                title="Pagination coming soon"
                className="cursor-not-allowed rounded border border-outline-variant p-1.5 text-on-surface-variant opacity-30"
              >
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button
                disabled
                title="Pagination coming soon"
                className="cursor-not-allowed rounded border border-outline-variant p-1.5 text-on-surface-variant opacity-30"
              >
                <span className="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="relative overflow-hidden rounded-xl border border-outline-variant bg-surface-container p-6 lg:col-span-8">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h4 className="font-headline-sm text-headline-sm text-on-surface">Real-time Call Metrics</h4>
              <p className="text-sm text-on-surface-variant">Active NPC interaction volume across shards</p>
            </div>
            <span className="material-symbols-outlined text-primary/40">monitoring</span>
          </div>
          <div className="flex h-48 w-full items-end gap-1 px-2">
            {METRIC_BAR_HEIGHTS.map((height, i) => (
              <div
                key={i}
                style={{ height: `${height}%` }}
                className="w-full rounded-t-sm bg-primary/20 transition-all hover:bg-primary/40"
              />
            ))}
          </div>
        </div>
        <div className="flex flex-col justify-between rounded-xl border border-outline-variant bg-surface-container p-6 lg:col-span-4">
          <div>
            <h4 className="mb-2 font-headline-sm text-headline-sm text-on-surface">Narrative Forge</h4>
            <p className="text-sm text-on-surface-variant">
              Connect your NPCs to multi-path storylines to create dynamic world states.
            </p>
          </div>
          <button
            onClick={onNavigateStorylines}
            className="mt-6 flex items-center gap-2 font-label-caps text-xs uppercase text-primary transition-all hover:gap-3"
          >
            Go to Storylines <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  );
}
