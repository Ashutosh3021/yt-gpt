import type {
  AddLinksResult,
  Api,
  AppSettings,
  ChatRequest,
  LlmSettings,
  Message,
  Session,
  SourceDoc,
  User,
  Workspace,
} from '../types';
import { ApiError } from './error';

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string; message?: string };
      message = body.detail ?? body.message ?? message;
    } catch {
      // Keep the status text.
    }
    throw new ApiError(message, res.status);
  }
  if (res.status === 204) return undefined as T;
  const type = res.headers.get('content-type') ?? '';
  if (type.includes('application/json')) return (await res.json()) as T;
  return (await res.text()) as T;
}

const json = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

async function streamMessage(
  workspaceId: string,
  sessionId: string,
  requestBody: ChatRequest,
  onToken: (text: string) => void,
): Promise<Message> {
  const res = await fetch(`${BASE}/api/workspaces/${workspaceId}/sessions/${sessionId}/messages`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: requestBody.content }),
    signal: requestBody.signal,
  });
  if (!res.ok || !res.body) throw new ApiError('The model did not answer.', res.status || 500);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let final: Message | null = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim();
      if (!payload || payload === '[DONE]') continue;
      try {
        const event = JSON.parse(payload) as {
          token?: string;
          message?: Message;
          error?: string;
          retryAfter?: number | null;
        };
        if (event.token) onToken(event.token);
        if (event.message) final = event.message;
        if (event.error) {
          const retryAfter = typeof event.retryAfter === 'number' ? event.retryAfter : undefined;
          throw new ApiError(event.error, retryAfter ? 429 : 400, retryAfter);
        }
      } catch (error) {
        if (error instanceof ApiError) throw error;
      }
    }
  }
  if (!final) throw new ApiError('The stream ended before the answer did.');
  return final;
}

const httpApi: Api = {
  auth: {
    me: () => request<User | null>('/api/auth/me'),
    signIn: (email, password) => request<User>('/api/auth/login', json({ email, password })),
    signUp: (name, email, password) => request<User>('/api/auth/signup', json({ name, email, password })),
    signOut: () => request<void>('/api/auth/logout', { method: 'POST' }),
    demo: () => {
      throw new ApiError('The demo workspace is only available in demo mode.');
    },
  },
  workspaces: {
    list: () => request<Workspace[]>('/api/workspaces'),
    get: (id) => request<Workspace>(`/api/workspaces/${id}`),
    create: (name) => request<Workspace>('/api/workspaces', json({ name })),
    rename: (id, name) => request<Workspace>(`/api/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify({ name }) }),
    updateSettings: (id, settings) =>
      request<Workspace>(`/api/workspaces/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ settings }),
      }),
    remove: (id) => request<void>(`/api/workspaces/${id}`, { method: 'DELETE' }),
  },
  videos: {
    add: (workspaceId, links) =>
      request<AddLinksResult>(`/api/workspaces/${workspaceId}/videos`, json({ links })),
    retry: (workspaceId, videoId) =>
      request<void>(`/api/workspaces/${workspaceId}/videos/${videoId}/retry`, { method: 'POST' }),
    remove: (workspaceId, videoId) =>
      request<void>(`/api/workspaces/${workspaceId}/videos/${videoId}`, { method: 'DELETE' }),
    transcript: (workspaceId) => request<string>(`/api/workspaces/${workspaceId}/export`),
  },
  sessions: {
    create: (workspaceId, title) =>
      request<Session>(`/api/workspaces/${workspaceId}/sessions`, json({ title })),
    update: (workspaceId, sessionId, patch) =>
      request<Session>(`/api/workspaces/${workspaceId}/sessions/${sessionId}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      }),
    remove: (workspaceId, sessionId) =>
      request<void>(`/api/workspaces/${workspaceId}/sessions/${sessionId}`, { method: 'DELETE' }),
    send: (workspaceId, sessionId, req, onToken) => streamMessage(workspaceId, sessionId, req, onToken),
  },
  sources: {
    create: (workspaceId, name, content) =>
      request<SourceDoc>(`/api/workspaces/${workspaceId}/sources`, json({ name, content })),
    update: (workspaceId, name, content, note) =>
      request<SourceDoc>(`/api/workspaces/${workspaceId}/sources/${encodeURIComponent(name)}`, {
        method: 'PUT',
        body: JSON.stringify({ content, note }),
      }),
    remove: (workspaceId, name) =>
      request<void>(`/api/workspaces/${workspaceId}/sources/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    restore: (workspaceId, name, versionId) =>
      request<SourceDoc>(
        `/api/workspaces/${workspaceId}/sources/${encodeURIComponent(name)}/versions/${versionId}`,
        { method: 'POST' },
      ),
  },
  settings: {
    get: async () => {
      const llm = await request<LlmSettings>('/api/settings/llm');
      return {
        llm,
        root: '~/.yt-gpt',
        version: '1.0.0',
        doctor: [],
      } satisfies AppSettings;
    },
    saveLlm: async (patch) => {
      await request<LlmSettings>('/api/settings/llm', { method: 'PUT', body: JSON.stringify(patch) });
      const llm = await request<LlmSettings>('/api/settings/llm');
      return { llm, root: '~/.yt-gpt', version: '1.0.0', doctor: [] } satisfies AppSettings;
    },
    testLlm: () => request<{ ok: boolean; message: string }>('/api/settings/llm/test', { method: 'POST' }),
    rebuild: () => request<{ ok: boolean; message: string }>('/api/doctor/rebuild', { method: 'POST' }),
  },
  events: {
    subscribe: (workspaceId, listener) => {
      const source = new EventSource(`${BASE}/api/workspaces/${workspaceId}/events`, { withCredentials: true });
      source.onmessage = () => listener();
      source.onerror = () => {
        // EventSource reconnects on its own.
      };
      return () => source.close();
    },
  },
};

export const httpClient = httpApi;
