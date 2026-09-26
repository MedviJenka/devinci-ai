import { useState } from 'react';
import { BookOpen } from 'lucide-react';
import { NpcSummary } from '../types';
import Modal from './Modal';

interface Props {
  npcs: NpcSummary[];
  onCreate: (fields: { title: string; npcSlug: string; prompt: string }) => void;
  onClose: () => void;
}

const inputClass =
  'w-full rounded border border-outline-variant bg-surface-container-lowest p-3 font-body-md text-on-surface outline-none transition-colors focus:border-primary';
const labelClass = 'font-label-caps text-label-caps uppercase text-outline';

export default function CreateStorylineModal({ npcs, onCreate, onClose }: Props) {
  const [title, setTitle] = useState('');
  const [npcSlug, setNpcSlug] = useState(npcs[0]?.slug ?? '');
  const [prompt, setPrompt] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !npcSlug) return;
    onCreate({ title: title.trim(), npcSlug, prompt: prompt.trim() });
  };

  return (
    <Modal onClose={onClose}>
      <form
        onSubmit={submit}
        className="space-y-5 rounded-lg border border-outline-variant bg-surface-container p-6 shadow-[0_0_40px_-10px_rgba(208,188,255,0.15)]"
      >
        <div className="flex items-center gap-3 border-b border-outline-variant pb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 shadow-[0_0_14px_-4px_rgba(206,192,236,0.5)]">
            <BookOpen size={18} strokeWidth={1.75} className="text-primary" />
          </div>
          <h2 className="font-headline-sm text-headline-sm text-on-surface">New Storyline</h2>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. The Smith's Lost Apprentice"
            className={inputClass}
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Linked NPC</label>
          <select value={npcSlug} onChange={(e) => setNpcSlug(e.target.value)} className={inputClass}>
            {npcs.map((npc) => (
              <option key={npc.slug} value={npc.slug}>
                {npc.role}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Prompt (optional)</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            placeholder="What should this storyline be about?"
            className={inputClass}
          />
        </div>

        <p className="font-code-md text-[11px] text-outline">
          Saved as a local draft — story generation isn't connected yet.
        </p>

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded px-3 py-1.5 font-label-caps text-label-caps uppercase text-on-surface-variant hover:bg-surface-container-high"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim() || !npcSlug}
            className="rounded bg-primary px-4 py-1.5 font-label-caps text-label-caps uppercase text-on-primary hover:brightness-110 disabled:opacity-50"
          >
            Save Draft
          </button>
        </div>
      </form>
    </Modal>
  );
}
