import { ApiKeyCreateResponse, ApiKeySummary, NpcCreateRequest, NpcDetail, NpcSummary, NpcUpdateRequest } from './types';
import { supabase } from './supabaseClient';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5555/api/v1/npcs';
const CHARACTER_API_BASE = process.env.REACT_APP_CHARACTER_API_BASE || 'http://localhost:5555/api/v1/character';
const API_KEYS_BASE = process.env.REACT_APP_API_KEYS_BASE || 'http://localhost:5555/api/v1/api-keys';

async function authToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function request<T>(path: string, init?: RequestInit, base: string = API_BASE): Promise<T> {
  const token = await authToken();
  const res = await fetch(`${base}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) {
      await supabase.auth.signOut();
      throw new Error('Your session expired. Please sign in again.');
    }
    throw new Error(body.detail || `request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const listNpcs = () => request<NpcSummary[]>('/');

export const createNpc = (req: NpcCreateRequest) =>
  request<NpcDetail>('/', { method: 'POST', body: JSON.stringify(req) });

export const getNpc = (slug: string) => request<NpcDetail>(`/${slug}`);

export const updateNpc = (slug: string, req: NpcUpdateRequest) =>
  request<NpcDetail>(`/${slug}`, { method: 'PUT', body: JSON.stringify(req) });

export const deleteNpc = (slug: string) => request<void>(`/${slug}`, { method: 'DELETE' });

export const listApiKeys = () => request<ApiKeySummary[]>('/', {}, API_KEYS_BASE);

export const createApiKey = (name: string) =>
  request<ApiKeyCreateResponse>('/', { method: 'POST', body: JSON.stringify({ name }) }, API_KEYS_BASE);

export const revokeApiKey = (id: string) => request<void>(`/${id}`, { method: 'DELETE' }, API_KEYS_BASE);

export interface GenerateCharacterResult {
  success: boolean;
  file_location: string;
  description: string;
  persona: string;
  error?: string;
}

export const generateCharacter = (npcName: string, prompt: string) => {
  const params = new URLSearchParams({ query: prompt, npc_name: npcName });
  return request<GenerateCharacterResult>(`/create?${params.toString()}`, { method: 'POST' }, CHARACTER_API_BASE);
};

export interface TalkHandlers {
  onChunk?: (text: string) => void;
  onDone: (text: string, mood?: string) => void;
  onError: (message: string) => void;
}

export function streamTalk(slug: string, query: string, handlers: TalkHandlers): () => void {
  let source: EventSource | null = null;
  let closed = false;

  // EventSource can't set custom headers, so the token travels as a query param instead.
  authToken().then((token) => {
    if (closed) return;
    const params = new URLSearchParams({ query, ...(token ? { token } : {}) });
    source = new EventSource(`${API_BASE}/${encodeURIComponent(slug)}/talk?${params.toString()}`);

    source.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'chunk') {
        handlers.onChunk?.(data.text);
      } else if (data.type === 'done') {
        handlers.onDone(data.text, data.mood);
        source?.close();
      } else if (data.type === 'error') {
        handlers.onError(data.message);
        source?.close();
      }
    };

    source.onerror = () => {
      handlers.onError('Connection lost.');
      source?.close();
    };
  });

  return () => {
    closed = true;
    source?.close();
  };
}
