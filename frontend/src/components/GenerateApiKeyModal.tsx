import { useState } from 'react';

interface Props {
  onGenerate: (name: string) => void;
  onClose: () => void;
}

const inputClass =
  'w-full rounded border border-outline-variant bg-surface-container-lowest p-3 font-body-md text-on-surface outline-none transition-colors focus:border-primary';
const labelClass = 'font-label-caps text-label-caps uppercase text-outline';

export default function GenerateApiKeyModal({ onGenerate, onClose }: Props) {
  const [name, setName] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onGenerate(name.trim());
  };

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <form
        onSubmit={submit}
        className="w-full max-w-md space-y-5 rounded-lg border border-outline-variant bg-surface-container p-6 shadow-[0_0_40px_-10px_rgba(208,188,255,0.15)]"
      >
        <div className="flex items-center gap-3 border-b border-outline-variant pb-4">
          <span className="material-symbols-outlined text-primary">vpn_key</span>
          <h2 className="font-headline-sm text-headline-sm text-on-surface">Generate API Key</h2>
        </div>

        <div className="space-y-2">
          <label className={labelClass}>Key Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Production_Orchestrator_Main"
            className={inputClass}
          />
        </div>

        <p className="font-code-md text-[11px] text-outline">
          You'll see the full key once, right after it's generated — copy it somewhere safe.
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
            disabled={!name.trim()}
            className="rounded bg-primary px-4 py-1.5 font-label-caps text-label-caps uppercase text-on-primary hover:brightness-110 disabled:opacity-50"
          >
            Generate
          </button>
        </div>
      </form>
    </div>
  );
}
