import { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import type { Session } from '@supabase/supabase-js';
import { createNpc, deleteNpc, getNpc, listNpcs, resetNpcMemory, updateNpc } from './api';
import { supabase } from './supabaseClient';
import Sidebar, { Screen } from './components/Sidebar';
import Library from './components/Library';
import Dashboard from './components/Dashboard';
import Storylines from './components/Storylines';
import ApiKeys from './components/ApiKeys';
import CreateNpcModal from './components/CreateNpcModal';
import ConfirmDialog from './components/ConfirmDialog';
import PersonaEditor from './components/PersonaEditor';
import Chat from './components/Chat';
import SignIn from './components/SignIn';
import Toast, { ToastData } from './components/Toast';
import { AuditEntry } from './components/NotificationsBell';
import { NpcCreateRequest, NpcDetail, NpcSummary, NpcUpdateRequest } from './types';

type Tab = 'persona' | 'chat';

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [screen, setScreen] = useState<Screen>('npcs');
  const [npcs, setNpcs] = useState<NpcSummary[]>([]);
  const [npcsLoading, setNpcsLoading] = useState(true);
  const [selected, setSelected] = useState<NpcDetail | null>(null);
  const [isNewNpc, setIsNewNpc] = useState(false);
  const [tab, setTab] = useState<Tab>('chat');
  const [showCreate, setShowCreate] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [deletingSlug, setDeletingSlug] = useState<string | null>(null);
  const [confirmDeleteSlug, setConfirmDeleteSlug] = useState<string | null>(null);
  const [deletingSlugs, setDeletingSlugs] = useState<Set<string>>(new Set());
  const [confirmDeleteSlugs, setConfirmDeleteSlugs] = useState<string[] | null>(null);
  const [resettingMemory, setResettingMemory] = useState(false);
  const [confirmResetMemory, setConfirmResetMemory] = useState(false);

  const navigate = (next: Screen) => {
    setScreen(next);
    setSelected(null);
    setIsNewNpc(false);
  };

  const notify = (type: 'success' | 'error', message: string) => {
    const entry = { id: crypto.randomUUID(), type, message, timestamp: Date.now() };
    setAudit((prev) => [entry, ...prev].slice(0, 50));
    setToast(entry);
  };

  const refreshList = async () => {
    setNpcs(await listNpcs());
  };

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setAuthLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session) return;
    refreshList()
      .then(() => notify('success', 'Backend connected successfully.'))
      .catch((err) => notify('error', err.message))
      .finally(() => setNpcsLoading(false));
  }, [session]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), toast.type === 'success' ? 3000 : 5000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  if (authLoading) {
    return <div className="flex h-screen items-center justify-center bg-background" />;
  }

  if (!session) {
    return <SignIn onSignedIn={() => {}} />;
  }

  const openNpc = async (slug: string, initialTab: Tab) => {
    try {
      setSelected(await getNpc(slug));
      setIsNewNpc(false);
      setTab(initialTab);
      setScreen('npcs');
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Failed to load NPC.');
    }
  };

  const handleCreate = async (req: NpcCreateRequest) => {
    const created = await createNpc(req);
    await refreshList();
    setSelected(created);
    setIsNewNpc(true);
    setTab('persona');
    setScreen('npcs');
    setShowCreate(false);
  };

  const handleDelete = (slug: string) => setConfirmDeleteSlug(slug);

  const confirmDelete = async () => {
    const slug = confirmDeleteSlug;
    if (!slug) return;
    setConfirmDeleteSlug(null);
    setDeletingSlug(slug);
    try {
      await deleteNpc(slug);
      if (selected?.slug === slug) setSelected(null);
      await refreshList();
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Failed to delete NPC.');
    } finally {
      setDeletingSlug(null);
    }
  };

  const handleBulkDelete = (slugs: string[]) => setConfirmDeleteSlugs(slugs);

  const confirmBulkDelete = async () => {
    const slugs = confirmDeleteSlugs;
    if (!slugs || slugs.length === 0) return;
    setConfirmDeleteSlugs(null);
    setDeletingSlugs(new Set(slugs));
    try {
      const results = await Promise.allSettled(slugs.map((slug) => deleteNpc(slug)));
      const failed = results.filter((r) => r.status === 'rejected').length;
      if (selected && slugs.includes(selected.slug)) setSelected(null);
      await refreshList();
      if (failed > 0) {
        notify('error', `Failed to delete ${failed} of ${slugs.length} NPCs.`);
      } else {
        notify('success', `Deleted ${slugs.length} NPC${slugs.length === 1 ? '' : 's'}.`);
      }
    } finally {
      setDeletingSlugs(new Set());
    }
  };

  const handleResetMemory = () => setConfirmResetMemory(true);

  const confirmResetMemoryAction = async () => {
    if (!selected) return;
    setConfirmResetMemory(false);
    setResettingMemory(true);
    try {
      await resetNpcMemory(selected.slug);
      notify('success', `Cleared memory for "${selected.slug}".`);
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Failed to clear memory.');
    } finally {
      setResettingMemory(false);
    }
  };

  const handleSave = async (fields: NpcUpdateRequest) => {
    if (!selected) return;
    const updated = await updateNpc(selected.slug, fields);
    await refreshList();
    if (isNewNpc) {
      setIsNewNpc(false);
      setSelected(null);
    } else {
      setSelected(updated);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background font-body-md text-on-surface">
      <Toast toast={toast} />

      <Sidebar
        activeScreen={screen}
        onNavigate={navigate}
        userEmail={session.user.email}
        onSignOut={() => supabase.auth.signOut()}
      />

      <main className="flex min-w-0 flex-1 flex-col">

        {screen === 'dashboard' && (
          <Dashboard
            npcs={npcs}
            loading={npcsLoading}
            onOpenChat={(slug) => openNpc(slug, 'chat')}
            onCreate={() => setShowCreate(true)}
          />
        )}

        {screen === 'storylines' && <Storylines npcs={npcs} />}

        {screen === 'api-keys' && <ApiKeys />}

        {screen === 'npcs' && !selected && (
          <Library
            npcs={npcs}
            loading={npcsLoading}
            deletingSlug={deletingSlug}
            deletingSlugs={deletingSlugs}
            audit={audit}
            onOpenChat={(slug) => openNpc(slug, 'chat')}
            onOpenPersona={(slug) => openNpc(slug, 'persona')}
            onDelete={handleDelete}
            onBulkDelete={handleBulkDelete}
            onCreate={() => setShowCreate(true)}
            onNavigateStorylines={() => navigate('storylines')}
          />
        )}

        {screen === 'npcs' && selected && (
          <>
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface-container px-gutter">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => {
                    setSelected(null);
                    setIsNewNpc(false);
                  }}
                  title="Back to library"
                  className="rounded p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
                >
                  <ArrowLeft size={18} strokeWidth={1.75} />
                </button>
                <h2 className="font-headline-sm text-headline-sm text-on-surface">{selected.role}</h2>
                <span className="rounded bg-surface-container-highest px-2 py-1 font-code-md text-code-md text-outline">
                  {selected.llm}
                </span>
              </div>
              <div className="flex gap-1 rounded bg-surface-container-high p-1">
                <button
                  onClick={() => setTab('chat')}
                  className={`rounded px-4 py-1.5 font-label-caps text-label-caps uppercase transition-colors ${
                    tab === 'chat' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Chat
                </button>
                <button
                  onClick={() => setTab('persona')}
                  className={`rounded px-4 py-1.5 font-label-caps text-label-caps uppercase transition-colors ${
                    tab === 'persona' ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  Persona
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1">
              {tab === 'chat' ? (
                <Chat slug={selected.slug} structuredOutput={selected.pydantic_enabled} />
              ) : (
                <div className="h-full overflow-y-auto custom-scrollbar bg-background">
                  <PersonaEditor
                    npc={selected}
                    onSave={handleSave}
                    onResetMemory={handleResetMemory}
                    resettingMemory={resettingMemory}
                  />
                </div>
              )}
            </div>
          </>
        )}
      </main>

      {showCreate && <CreateNpcModal onCreate={handleCreate} onClose={() => setShowCreate(false)} />}

      {confirmDeleteSlug && (
        <ConfirmDialog
          title="Delete this NPC?"
          message={`"${confirmDeleteSlug}" will be permanently removed. This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={confirmDelete}
          onCancel={() => setConfirmDeleteSlug(null)}
        />
      )}

      {confirmDeleteSlugs && (
        <ConfirmDialog
          title={`Delete ${confirmDeleteSlugs.length} NPC${confirmDeleteSlugs.length === 1 ? '' : 's'}?`}
          message={`${confirmDeleteSlugs.length} NPC${confirmDeleteSlugs.length === 1 ? '' : 's'} will be permanently removed. This cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={confirmBulkDelete}
          onCancel={() => setConfirmDeleteSlugs(null)}
        />
      )}

      {confirmResetMemory && selected && (
        <ConfirmDialog
          title="Clear this NPC's memory?"
          message={`All conversation memory for "${selected.slug}" will be permanently erased. This cannot be undone.`}
          confirmLabel="Clear memory"
          onConfirm={confirmResetMemoryAction}
          onCancel={() => setConfirmResetMemory(false)}
        />
      )}
    </div>
  );
}

export default App;
