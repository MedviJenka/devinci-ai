import { useState } from 'react';
import { NpcCreateRequest } from '../types';

interface Props {
  onCreate: (req: NpcCreateRequest) => Promise<void>;
  onClose: () => void;
}

const inputClass =
  'w-full rounded border border-outline-variant bg-surface-container-lowest p-3 font-body-md text-on-surface outline-none transition-colors focus:border-primary';
const labelClass = 'font-label-caps text-label-caps uppercase text-outline';

export default function CreateNpcModal({ onCreate, onClose }: Props) {
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [backstory, setBackstory] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await onCreate({ name, goal: goal || undefined, backstory: backstory || undefined });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create NPC.');
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <form
        onSubmit={submit}
        className="w-full max-w-md space-y-5 rounded-lg border border-outline-variant bg-surface-container p-6 shadow-[0_0_40px_-10px_rgba(208,188,255,0.15)]"
      >
        <div className="flex items-center gap-3 border-b border-outline-variant pb-4">
          <span className="material-symbols-outlined text-primary">person_add</span>
          <h2 className="font-headline-sm text-headline-sm text-on-surface">Create NPC</h2>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Name</label>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Aldric the Smith"
            className={inputClass}
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Goal (optional)</label>
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="interactive npc"
            className={inputClass}
          />
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Backstory (optional)</label>
          <textarea
            value={backstory}
            onChange={(e) => setBackstory(e.target.value)}
            rows={3}
            placeholder="Short teaser backstory..."
            className={inputClass}
          />
        </div>

        {error && <p className="text-sm text-error">{error}</p>}

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
            disabled={!name.trim() || submitting}
            className="rounded bg-primary px-4 py-1.5 font-label-caps text-label-caps uppercase text-on-primary hover:brightness-110 disabled:opacity-50"
          >
            {submitting ? 'Creating...' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  );
}
