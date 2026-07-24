import { TriangleAlert, CircleHelp } from 'lucide-react';
import Modal from './Modal';

interface Props {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = true,
  onConfirm,
  onCancel,
}: Props) {
  return (
    <Modal onClose={onCancel}>
      <div className="animate-fade-in rounded-xl border border-outline-variant bg-surface-container-high p-6 shadow-2xl">
        <div className="flex items-start gap-4">
          <div
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${
              danger ? 'bg-error/15 text-error' : 'bg-primary/15 text-primary'
            }`}
          >
            {danger ? (
              <TriangleAlert size={20} strokeWidth={1.75} />
            ) : (
              <CircleHelp size={20} strokeWidth={1.75} />
            )}
          </div>
          <div className="min-w-0 pt-1">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">{title}</h3>
            <p className="mt-1.5 text-body-md text-on-surface-variant">{message}</p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-lg border border-outline-variant px-4 py-2 font-label-caps text-label-caps uppercase text-on-surface-variant transition-colors hover:bg-surface-container-highest hover:text-on-surface"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            autoFocus
            className={`rounded-lg px-4 py-2 font-label-caps text-label-caps uppercase transition-all active:scale-[0.98] ${
              danger
                ? 'bg-error text-on-error shadow-lg shadow-error/20 hover:brightness-110'
                : 'bg-primary text-on-primary shadow-lg shadow-primary/20 hover:brightness-110'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
