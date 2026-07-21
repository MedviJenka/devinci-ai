import LogoIcon from './icons/LogoIcon';

export type Screen = 'dashboard' | 'npcs' | 'storylines' | 'api-keys';

interface NavItem {
  icon: string;
  label: string;
  screen?: Screen;
  disabled?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { icon: 'dashboard', label: 'Dashboard', screen: 'dashboard' },
  { icon: 'smart_toy', label: 'NPCs', screen: 'npcs' },
  { icon: 'auto_stories', label: 'Storylines', screen: 'storylines' },
  { icon: 'vpn_key', label: 'API Keys', screen: 'api-keys' },
  { icon: 'payments', label: 'Usage & Billing', disabled: true },
];

interface Props {
  activeScreen: Screen;
  onNavigate: (screen: Screen) => void;
  onCreate: () => void;
  userEmail?: string | null;
  onSignOut?: () => void;
}

export default function Sidebar({ activeScreen, onNavigate, onCreate, userEmail, onSignOut }: Props) {
  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-outline-variant bg-surface-container py-6">
      <div className="mb-8 px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary">
            <LogoIcon className="h-5 w-5 text-on-primary" />
          </div>
          <div>
            <h1 className="font-headline-md text-headline-md font-bold leading-none tracking-tight text-on-surface">
              Devinci
            </h1>
            <p className="mt-1 font-label-caps text-[9px] uppercase tracking-[0.2em] text-primary">NPC Studio</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = !item.disabled && item.screen === activeScreen;
          return (
            <div
              key={item.label}
              onClick={() => !item.disabled && item.screen && onNavigate(item.screen)}
              className={`flex items-center justify-between gap-3 border-l-2 px-4 py-3 transition-colors ${
                item.disabled ? 'cursor-default' : 'cursor-pointer'
              } ${
                active
                  ? 'border-primary bg-primary/5 text-primary'
                  : item.disabled
                    ? 'border-transparent text-outline/50'
                    : 'border-transparent text-on-surface-variant hover:bg-surface-container-high'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                <span className="font-label-caps text-label-caps uppercase">{item.label}</span>
              </div>
              {item.disabled && (
                <span className="rounded bg-surface-container-highest px-1.5 py-0.5 font-code-md text-[9px] uppercase tracking-wide text-outline">
                  Soon
                </span>
              )}
            </div>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3 px-4">
        <button
          onClick={onCreate}
          className="flex w-full items-center justify-center gap-2 rounded bg-primary py-3 font-label-caps text-label-caps text-on-primary transition-all hover:brightness-110 active:scale-[0.98]"
        >
          <span className="material-symbols-outlined text-[18px]">add</span>
          New NPC
        </button>

        {userEmail && (
          <div className="flex items-center justify-between gap-2 rounded border border-outline-variant px-3 py-2">
            <span className="truncate font-body-md text-sm text-on-surface-variant" title={userEmail}>
              {userEmail}
            </span>
            <button
              onClick={onSignOut}
              title="Sign out"
              className="shrink-0 rounded p-1 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-[18px]">logout</span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
