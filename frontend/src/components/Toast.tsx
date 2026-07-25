import { useEffect, useState } from 'react';

export interface ToastData {
  id: string;
  type: 'success' | 'error';
  message: string;
}

interface Props {
  toast: ToastData | null;
}

export default function Toast({ toast }: Props) {
  const [rendered, setRendered] = useState<ToastData | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!toast) {
      setVisible(false);
      return;
    }
    setRendered(toast);
    const frame = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(frame);
  }, [toast]);

  if (!rendered) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center">
      <div
        onTransitionEnd={() => {
          if (!visible) setRendered(null);
        }}
        className={`pointer-events-auto max-w-md rounded-xl border px-5 py-3 text-sm shadow-xl backdrop-blur-md transition-all duration-300 ease-out ${
          visible ? 'translate-y-0 opacity-100' : '-translate-y-3 opacity-0'
        } ${
          rendered.type === 'success'
            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
            : 'border-error/30 bg-error-container/20 text-on-error-container'
        }`}
      >
        {rendered.message}
      </div>
    </div>
  );
}
