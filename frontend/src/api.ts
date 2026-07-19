import { NpcCreateRequest, NpcDetail, NpcSummary, NpcUpdateRequest } from './types';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:5555/api/v1/npcs';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
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

export interface TalkHandlers {
  onChunk?: (text: string) => void;
  onDone: (text: string, mood?: string) => void;
  onError: (message: string) => void;
}

export function streamTalk(slug: string, query: string, handlers: TalkHandlers): () => void {
  const url = `${API_BASE}/${encodeURIComponent(slug)}/talk?query=${encodeURIComponent(query)}`;
  const source = new EventSource(url);

  source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'chunk') {
      handlers.onChunk?.(data.text);
    } else if (data.type === 'done') {
      handlers.onDone(data.text, data.mood);
      source.close();
    } else if (data.type === 'error') {
      handlers.onError(data.message);
      source.close();
    }
  };

  source.onerror = () => {
    handlers.onError('Connection lost.');
    source.close();
  };

  return () => source.close();
}
