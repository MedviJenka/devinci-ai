import { useEffect, useRef, useState } from 'react';
import { Bell } from 'lucide-react';

export interface AuditEntry {
  id: string;
  type: 'success' | 'error';
  message: string;
  timestamp: number;
}

interface Props {
  entries: AuditEntry[];
}

export default function NotificationsBell({ entries }: Props) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="System audit"
        aria-expanded={open}
        className="relative rounded-lg p-2 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
      >
        <Bell size={18} strokeWidth={1.75} />
        {entries.length > 0 && (
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_6px_1px_rgba(208,188,255,0.7)]" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-xl border border-outline-variant bg-surface-container shadow-2xl">
          <div className="border-b border-outline-variant px-4 py-3">
            <h3 className="font-label-caps text-label-caps uppercase text-on-surface-variant">System Audit</h3>
          </div>
          <div className="max-h-80 divide-y divide-outline-variant/30 overflow-y-auto custom-scrollbar">
            {entries.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-outline">No activity yet.</p>
            ) : (
              entries.map((entry) => (
                <div key={entry.id} className="flex items-start gap-2 px-4 py-3">
                  <span
                    className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                      entry.type === 'success' ? 'bg-emerald-400' : 'bg-error'
                    }`}
                  />
                  <div className="min-w-0">
                    <p className="text-sm text-on-surface">{entry.message}</p>
                    <p className="mt-0.5 font-code-md text-[11px] text-outline">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
