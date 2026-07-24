import { useEffect, useMemo, useRef, useState } from 'react';
import { Search, Plus, Bot, Loader2, Pencil, BarChart3, Trash2, ChevronLeft, ChevronRight, Activity, ArrowRight } from 'lucide-react';
import { NpcSummary } from '../types';

interface Props {
  npcs: NpcSummary[];
  loading?: boolean;
  deletingSlug?: string | null;
  onOpenChat: (slug: string) => void;
  onOpenPersona: (slug: string) => void;
  onDelete: (slug: string) => void;
  onCreate: () => void;
  onNavigateStorylines?: () => void;
}

function SkeletonBar({ className }: { className: string }) {
  return <div className={`shimmer rounded bg-surface-container-highest ${className}`} />;
}

export default function Library({
  npcs,
  loading,
  deletingSlug,
  onOpenChat,
  onOpenPersona,
  onDelete,
  onCreate,
  onNavigateStorylines,
}: Props) {
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
      <div className="mb-8 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
        <div className="min-w-0">
          <h2 className="font-headline-lg text-headline-lg text-on-surface">Entity Library</h2>
          <p className="mt-1 text-on-surface-variant">Manage your narrative intelligence components.</p>
        </div>
        <div className="relative w-[28rem] max-w-full">
          <Search
            size={14}
            strokeWidth={1.75}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant"
          />
          <input
            ref={searchRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by role, goal, or persona traits..."
            className="h-9 w-full rounded-lg border border-outline-variant bg-surface-container pl-10 pr-10 text-body-md text-on-surface outline-none transition-shadow focus:ring-1 focus:ring-primary"
          />
          {!query && (
            <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded border border-outline-variant bg-surface-container-high px-1.5 py-0.5 font-code-md text-[10px] text-on-surface-variant">
              /
            </kbd>
          )}
        </div>
        <div className="flex justify-end">
          {npcs.length > 0 && (
            <div className="animate-gradient-flow rounded-lg bg-gradient-to-r from-cyan-400 via-purple-500 to-emerald-400 p-[2px]">
              <button
                onClick={onCreate}
                title="Create a new NPC"
                className="flex h-8 items-center gap-1.5 rounded-[calc(theme(borderRadius.lg)-2px)] bg-surface-container-lowest px-4 font-label-caps text-label-caps uppercase text-on-surface shadow-[0_0_16px_-4px_rgba(206,192,236,0.6)] transition-all hover:brightness-110 active:scale-[0.98]"
              >
                <Plus size={18} strokeWidth={1.75} />
                Add NPC
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-outline-variant bg-surface-container shadow-2xl">
        {loading ? (
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
                {Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <SkeletonBar className="h-8 w-8 shrink-0" />
                        <div className="min-w-0 flex-1 space-y-2">
                          <SkeletonBar className="h-3 w-32" />
                          <SkeletonBar className="h-2.5 w-48" />
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <SkeletonBar className="h-5 w-24" />
                    </td>
                    <td className="px-6 py-4">
                      <SkeletonBar className="h-3 w-20" />
                    </td>
                    <td className="px-6 py-4">
                      <SkeletonBar className="h-3 w-16" />
                    </td>
                    <td className="px-6 py-4">
                      <SkeletonBar className="h-3 w-12" />
                    </td>
                    <td className="px-6 py-4">
                      <div className="ml-auto flex w-fit gap-1.5">
                        <SkeletonBar className="h-7 w-7" />
                        <SkeletonBar className="h-7 w-7" />
                        <SkeletonBar className="h-7 w-7" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : filtered.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-high/50">
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Name</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">ID</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Status</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Last Called</th>
                  <th className="px-6 py-4 font-label-caps uppercase tracking-wider text-on-surface-variant">Call Count</th>
                  <th className="px-6 py-4 text-right font-label-caps uppercase tracking-wider text-on-surface-variant">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30">
                {filtered.map((npc) => {
                  const isDeleting = npc.slug === deletingSlug;
                  return (
                    <tr
                      key={npc.slug}
                      onClick={() => !isDeleting && onOpenChat(npc.slug)}
                      aria-busy={isDeleting}
                      className={`group border-l-2 transition-colors ${
                        isDeleting
                          ? 'cursor-default border-l-error/60 bg-error-container/5'
                          : 'cursor-pointer border-l-transparent hover:bg-primary/5'
                      }`}
                    >
                      <td className="px-4 py-4">
                        <div className={`flex items-center gap-3 transition-opacity ${isDeleting ? 'opacity-40' : ''}`}>
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
                            <Bot size={16} strokeWidth={1.75} className="text-primary" />
                          </div>
                          <div className="min-w-0">
                            <p className="truncate font-medium text-on-surface">{npc.role}</p>
                            <p className="truncate text-xs text-outline">{npc.goal}</p>
                          </div>
                        </div>
                      </td>
                      <td className={`px-6 py-4 transition-opacity ${isDeleting ? 'opacity-40' : ''}`}>
                        <span className="rounded bg-surface-container-lowest px-2 py-1 font-code-md text-code-md text-on-surface-variant">
                          {npc.slug}
                        </span>
                      </td>
                      <td className={`px-6 py-4 transition-opacity ${isDeleting ? 'opacity-40' : ''}`}>
                        <div className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_1px_rgba(52,211,153,0.5)]" />
                          <span className="font-label-caps text-xs uppercase text-emerald-400">Published</span>
                        </div>
                      </td>
                      <td className={`px-6 py-4 text-sm text-on-surface-variant transition-opacity ${isDeleting ? 'opacity-40' : ''}`}>
                        —
                      </td>
                      <td className={`px-6 py-4 font-code-md text-on-surface-variant transition-opacity ${isDeleting ? 'opacity-40' : ''}`}>
                        —
                      </td>
                      <td className="px-6 py-4 text-right">
                        {isDeleting ? (
                          <div className="ml-auto flex h-8 w-24 items-center justify-center gap-2 text-error">
                            <Loader2 size={18} strokeWidth={1.75} className="animate-spin" />
                            <span className="font-label-caps text-[10px] uppercase">Deleting</span>
                          </div>
                        ) : (
                          <div className="ml-auto inline-flex gap-0.5 rounded-lg p-0.5 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenPersona(npc.slug);
                              }}
                              title="Edit persona"
                              className="rounded-md p-2 text-on-surface-variant transition-all hover:bg-surface-container-highest hover:text-primary"
                            >
                              <Pencil size={18} strokeWidth={1.75} />
                            </button>
                            <button
                              onClick={(e) => e.stopPropagation()}
                              disabled
                              title="Analytics — coming soon"
                              className="cursor-not-allowed rounded-md p-2 text-on-surface-variant/40"
                            >
                              <BarChart3 size={18} strokeWidth={1.75} />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onDelete(npc.slug);
                              }}
                              disabled={!!deletingSlug}
                              title="Delete NPC"
                              className="rounded-md p-2 text-on-surface-variant transition-all hover:bg-surface-container-highest hover:text-error disabled:pointer-events-none disabled:opacity-40"
                            >
                              <Trash2 size={18} strokeWidth={1.75} />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (

          <div className="overflow-hidden py-12 text-center">
            <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-surface-container-high shadow-[0_0_40px_-10px_rgba(208,188,255,0.2)]">
              <Bot size={36} strokeWidth={1.5} className="text-primary/60" />
            </div>
            <div className="relative items-center z-10">
              <h3 className="items-center mb-2 font-headline-md text-headline-md text-on-surface">
                {npcs.length === 0 ? 'The Archive is Silent' : 'No matches found'}
              </h3>
              <p className="mx-auto mb-8 max-w-md text-on-surface-variant">
                {npcs.length === 0
                  ? 'No entities were found. Ready to forge your first narrative intelligence?'
                  : 'No NPCs match your current search.'}
              </p>
              {npcs.length === 0 && (
                <div className="inline-block animate-gradient-flow rounded-lg bg-gradient-to-r from-cyan-400 via-purple-500 to-emerald-400 p-[2px]">
                  <button
                    onClick={onCreate}
                    title="Create a new NPC"
                    className="flex items-center gap-1.5 rounded-[calc(theme(borderRadius.lg)-2px)] bg-surface-container-lowest px-8 py-3 font-label-caps text-label-caps uppercase text-on-surface shadow-[0_0_16px_-4px_rgba(206,192,236,0.6)] transition-all hover:brightness-110 active:scale-[0.98]"
                  >
                    <Plus size={18} strokeWidth={1.75} />
                    Create New NPC
                  </button>
                </div>
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
                <ChevronLeft size={14} strokeWidth={1.75} />
              </button>
              <button
                disabled
                title="Pagination coming soon"
                className="cursor-not-allowed rounded border border-outline-variant p-1.5 text-on-surface-variant opacity-30"
              >
                <ChevronRight size={14} strokeWidth={1.75} />
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="relative overflow-hidden rounded-xl border border-outline-variant bg-surface-container p-6 lg:col-span-8">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h4 className="font-headline-sm text-headline-sm text-on-surface">Call Metrics</h4>
              <p className="text-sm text-on-surface-variant">NPC interaction volume over time</p>
            </div>
            <span className="rounded bg-surface-container-highest px-1.5 py-0.5 font-code-md text-[9px] uppercase tracking-wide text-outline">
              Soon
            </span>
          </div>
          <div className="flex h-48 w-full flex-col items-center justify-center gap-2 text-center">
            <Activity size={28} strokeWidth={1.5} className="text-primary/40" />
            <p className="max-w-xs text-sm text-on-surface-variant">
              Live call volume will appear here once usage tracking ships.
            </p>
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
            Go to Storylines <ArrowRight size={14} strokeWidth={1.75} />
          </button>
        </div>
      </div>
    </div>
  );
}
