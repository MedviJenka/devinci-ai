import { useState } from 'react';
import { NpcSummary, Storyline } from '../types';
import CreateStorylineModal from './CreateStorylineModal';

interface Props {
  npcs: NpcSummary[];
}

export default function Storylines({ npcs }: Props) {
  const [storylines, setStorylines] = useState<Storyline[]>([]);
  const [showCreate, setShowCreate] = useState(false);

  const npcRole = (slug: string) => npcs.find((n) => n.slug === slug)?.role ?? slug;

  const handleCreate = (fields: { title: string; npcSlug: string; prompt: string }) => {
    setStorylines((prev) => [
      { id: crypto.randomUUID(), createdAt: new Date().toISOString(), ...fields },
      ...prev,
    ]);
    setShowCreate(false);
  };

  const handleDelete = (id: string) => {
    setStorylines((prev) => prev.filter((s) => s.id !== id));
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar bg-surface-container-lowest p-gutter">
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">Storylines</h2>
          <p className="mt-1 text-on-surface-variant">Draft narrative arcs for your NPCs.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          disabled={npcs.length === 0}
          title={npcs.length === 0 ? 'Create an NPC first' : undefined}
          className="flex items-center gap-2 rounded bg-primary px-4 py-2 font-label-caps text-label-caps uppercase text-on-primary transition-all hover:brightness-110 disabled:opacity-50"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          New Storyline
        </button>
      </div>

      {storylines.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-outline-variant bg-surface-container py-32 text-center">
          <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-primary/20 bg-surface-container-high shadow-[0_0_40px_-10px_rgba(208,188,255,0.2)]">
            <span className="material-symbols-outlined text-4xl leading-none text-primary/60">auto_stories</span>
          </div>
          <h3 className="mb-2 font-headline-md text-headline-md text-on-surface">No storylines yet</h3>
          <p className="mx-auto mb-8 max-w-md text-on-surface-variant">
            {npcs.length === 0
              ? 'Create an NPC first, then draft a storyline for them.'
              : 'Draft your first narrative arc. Storylines are saved locally for now — skill_agent generation is coming soon.'}
          </p>
          {npcs.length > 0 && (
            <button
              onClick={() => setShowCreate(true)}
              className="rounded-lg bg-primary px-8 py-3 font-label-caps text-label-caps uppercase text-on-primary shadow-lg shadow-primary/10 transition-all hover:brightness-110"
            >
              Draft First Storyline
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {storylines.map((s) => (
            <div key={s.id} className="rounded-xl border border-outline-variant bg-surface-container p-5">
              <div className="mb-3 flex items-start justify-between gap-2">
                <span className="rounded bg-surface-container-highest px-2 py-0.5 font-code-md text-[10px] uppercase tracking-wide text-outline">
                  Draft
                </span>
                <button
                  onClick={() => handleDelete(s.id)}
                  title="Delete draft"
                  className="rounded p-1 text-on-surface-variant transition-colors hover:bg-surface-container-highest hover:text-error"
                >
                  <span className="material-symbols-outlined text-[16px]">delete</span>
                </button>
              </div>
              <h3 className="mb-1 font-headline-sm text-headline-sm text-on-surface">{s.title}</h3>
              <p className="mb-3 font-code-md text-code-md text-primary">{npcRole(s.npcSlug)}</p>
              {s.prompt && <p className="line-clamp-3 text-sm text-on-surface-variant">{s.prompt}</p>}
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateStorylineModal npcs={npcs} onCreate={handleCreate} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
