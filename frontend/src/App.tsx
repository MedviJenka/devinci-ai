import { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import { createNpc, deleteNpc, getNpc, listNpcs, updateNpc } from './api';
import { supabase } from './supabaseClient';
import Sidebar, { Screen } from './components/Sidebar';
import Library from './components/Library';
import Dashboard from './components/Dashboard';
import Storylines from './components/Storylines';
import ApiKeys from './components/ApiKeys';
import CreateNpcModal from './components/CreateNpcModal';
import PersonaEditor from './components/PersonaEditor';
import Chat from './components/Chat';
import SignIn from './components/SignIn';
import { NpcCreateRequest, NpcDetail, NpcSummary } from './types';

type Tab = 'persona' | 'chat';

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [screen, setScreen] = useState<Screen>('npcs');
  const [npcs, setNpcs] = useState<NpcSummary[]>([]);
  const [selected, setSelected] = useState<NpcDetail | null>(null);
  const [tab, setTab] = useState<Tab>('chat');
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = (next: Screen) => {
    setScreen(next);
    setSelected(null);
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
    refreshList().catch((err) => setError(err.message));
  }, [session]);

  if (authLoading) {
    return <div className="flex h-screen items-center justify-center bg-background" />;
  }

  if (!session) {
    return <SignIn onSignedIn={() => {}} />;
  }

  const openNpc = async (slug: string, initialTab: Tab) => {
    setError(null);
    try {
      setSelected(await getNpc(slug));
      setTab(initialTab);
      setScreen('npcs');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load NPC.');
    }
  };

  const handleCreate = async (req: NpcCreateRequest) => {
    const created = await createNpc(req);
    await refreshList();
    setSelected(created);
    setTab('persona');
    setShowCreate(false);
  };

  const handleDelete = async (slug: string) => {
    if (!window.confirm(`Delete "${slug}"? This cannot be undone.`)) return;
    await deleteNpc(slug);
    if (selected?.slug === slug) setSelected(null);
    await refreshList();
  };

  const handleSave = async (fields: { goal: string; backstory: string; llm: string; persona_notes: string }) => {
    if (!selected) return;
    const updated = await updateNpc(selected.slug, fields);
    setSelected(updated);
    await refreshList();
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background font-body-md text-on-surface">
      <Sidebar
        activeScreen={screen}
        onNavigate={navigate}
        onCreate={() => setShowCreate(true)}
        userEmail={session.user.email}
        onSignOut={() => supabase.auth.signOut()}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        {error && (
          <div className="border-b border-error/30 bg-error-container/20 px-6 py-2 text-sm text-on-error-container">
            {error}
          </div>
        )}

        {screen === 'dashboard' && (
          <Dashboard npcs={npcs} onOpenChat={(slug) => openNpc(slug, 'chat')} onCreate={() => setShowCreate(true)} />
        )}

        {screen === 'storylines' && <Storylines npcs={npcs} />}

        {screen === 'api-keys' && <ApiKeys />}

        {screen === 'npcs' && !selected && (
          <Library
            npcs={npcs}
            onOpenChat={(slug) => openNpc(slug, 'chat')}
            onOpenPersona={(slug) => openNpc(slug, 'persona')}
            onDelete={handleDelete}
            onCreate={() => setShowCreate(true)}
          />
        )}

        {screen === 'npcs' && selected && (
          <>
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface-container px-gutter">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSelected(null)}
                  title="Back to library"
                  className="rounded p-1.5 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface"
                >
                  <span className="material-symbols-outlined">arrow_back</span>
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
                <Chat slug={selected.slug} />
              ) : (
                <div className="h-full overflow-y-auto custom-scrollbar bg-background">
                  <PersonaEditor npc={selected} onSave={handleSave} />
                </div>
              )}
            </div>
          </>
        )}
      </main>

      {showCreate && <CreateNpcModal onCreate={handleCreate} onClose={() => setShowCreate(false)} />}
    </div>
  );
}

export default App;
