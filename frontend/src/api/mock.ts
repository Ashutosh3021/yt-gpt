import type {
  AddLinksResult,
  Api,
  AppSettings,
  ChatRequest,
  LlmSettings,
  Message,
  Session,
  SessionSettings,
  SourceDoc,
  SourceVersion,
  User,
  Video,
  Workspace,
} from '../types';
import {
  DEMO_EMAIL,
  DEMO_PASSWORD,
  demoTranscript,
  demoUser,
  demoVideos,
  seedWorkspace,
} from '../data/demo';
import { site } from '../data/site';
import { ApiError } from './error';

const DB_KEY = 'ytgpt.demo.v4';
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
const now = () => new Date().toISOString();
const uid = (prefix: string) =>
  `${prefix}_${typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID().slice(0, 8) : Math.random().toString(36).slice(2, 10)}`;

interface Db {
  users: User[];
  passwords: Record<string, string>;
  workspaces: Workspace[];
  settings: Record<string, LlmSettings>;
  sessionUserId: string | null;
}

const defaultLlm = (): LlmSettings => ({
  provider: 'openai',
  baseUrl: 'https://api.openai.com/v1',
  model: 'gpt-4.1-mini',
  embeddingModel: 'text-embedding-3-small',
  hasKey: false,
  keyMasked: '',
  capabilities: { vision: true, tools: true, caching: true, contextK: 128 },
});

function freshDb(): Db {
  const demoWorkspace = seedWorkspace(demoUser.id);
  return {
    users: [demoUser],
    passwords: { [demoUser.id]: DEMO_PASSWORD },
    workspaces: [demoWorkspace],
    settings: { [demoUser.id]: defaultLlm() },
    sessionUserId: null,
  };
}

let db: Db | null = null;

function load(): Db {
  if (db) return db;
  try {
    const raw = localStorage.getItem(DB_KEY);
    if (raw) {
      db = JSON.parse(raw) as Db;
      return db;
    }
  } catch {
    // A broken demo store should reset rather than block the app.
  }
  db = freshDb();
  save();
  return db;
}

function save() {
  if (!db) return;
  try {
    localStorage.setItem(DB_KEY, JSON.stringify(db));
  } catch {
    // Quota errors are not fatal for the demo.
  }
}

function currentUser(): User {
  const user = load().users.find((u) => u.id === load().sessionUserId);
  if (!user) throw new ApiError('Sign in to continue.', 401);
  return user;
}

function ownedWorkspace(id: string): Workspace {
  const user = currentUser();
  const ws = load().workspaces.find((w) => w.id === id && w.ownerId === user.id);
  if (!ws) throw new ApiError('Workspace not found.', 404);
  return ws;
}

function touch(ws: Workspace) {
  ws.updatedAt = now();
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 48) || 'workspace';
}

function uniqueSlug(ownerId: string, base: string, exceptId?: string) {
  const taken = new Set(
    load()
      .workspaces.filter((w) => w.ownerId === ownerId && w.id !== exceptId)
      .map((w) => w.slug),
  );
  let slug = base;
  let i = 2;
  while (taken.has(slug)) slug = `${base}-${i++}`;
  return slug;
}

const listeners = new Map<string, Set<() => void>>();

function notify(workspaceId: string) {
  listeners.get(workspaceId)?.forEach((fn) => fn());
}

const timers = new Map<string, ReturnType<typeof setTimeout>[]>();

function clearTimers(videoId: string) {
  timers.get(videoId)?.forEach(clearTimeout);
  timers.delete(videoId);
}

function runJob(ws: Workspace, video: Video) {
  clearTimers(video.id);
  const schedule = (ms: number, fn: () => void) => {
    const list = timers.get(video.id) ?? [];
    list.push(setTimeout(fn, ms));
    timers.set(video.id, list);
  };
  const fail = video.youtubeId.includes('private') || video.url.includes('private');
  if (fail) {
    schedule(900, () => {
      video.status = 'failed';
      video.error = 'Video is private. Retry with a cookies file or remove it.';
      touch(ws);
      save();
      notify(ws.id);
    });
    return;
  }
  schedule(500, () => {
    video.status = 'fetching';
    save();
    notify(ws.id);
  });
  schedule(1200, () => {
    video.status = 'cleaning';
    save();
    notify(ws.id);
  });
  schedule(1900, () => {
    video.status = 'indexing';
    save();
    notify(ws.id);
  });
  schedule(2700, () => {
    video.status = 'ready';
    video.error = null;
    touch(ws);
    save();
    notify(ws.id);
  });
}

function resumeJobs() {
  const data = load();
  data.workspaces.forEach((ws) => {
    ws.videos.forEach((v) => {
      if (!['ready', 'failed'].includes(v.status)) runJob(ws, v);
    });
  });
}

const genericSegments = (title: string) => [
  { start: 0, end: 42, text: `${title} opens with the central question and a short map of the answer.` },
  { start: 43, end: 128, text: 'The first section sets up the vocabulary that the rest of the talk depends on.' },
  { start: 129, end: 245, text: 'The middle section works through an example, then generalizes it in one step.' },
  { start: 246, end: 390, text: 'The closing section names the limits of the approach and the next open question.' },
];

function makeVideo(youtubeId: string, url: string): Video {
  const known = demoVideos.find((v) => v.youtubeId === youtubeId);
  const base = known ?? null;
  const title = base?.title ?? `Pasted video ${youtubeId.slice(0, 6)}`;
  return {
    id: uid('v'),
    youtubeId,
    url,
    title,
    channel: base?.channel ?? 'Demo metadata',
    durationS: base?.durationS ?? 390,
    language: 'en',
    transcriptSource: base?.transcriptSource ?? 'auto',
    status: 'queued',
    error: null,
    addedAt: now(),
    tokens: base?.tokens ?? 1200,
    summary: base?.summary ?? 'A sample transcript for a pasted link. The demo runtime does not fetch metadata.',
    segments: base ? structuredClone(base.segments) : genericSegments(title),
    visual: { enabled: false, status: 'none', frames: 0 },
    demo: true,
  };
}

function parseLinks(input: string): { ids: string[]; invalid: string[]; playlist: boolean } {
  const lines = input
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  const ids: string[] = [];
  const invalid: string[] = [];
  let playlist = false;
  for (const line of lines) {
    let url: URL;
    try {
      url = new URL(line.startsWith('http') ? line : `https://${line}`);
    } catch {
      invalid.push(line);
      continue;
    }
    const host = url.hostname.replace(/^www\.|^m\./, '');
    if (!['youtube.com', 'youtu.be', 'music.youtube.com'].includes(host)) {
      invalid.push(line);
      continue;
    }
    const v = url.searchParams.get('v');
    const short = url.pathname.match(/^\/(shorts|live|embed)\/([\w-]{6,})/)?.[2];
    const be = host === 'youtu.be' ? url.pathname.slice(1).match(/^([\w-]{6,})/)?.[1] : null;
    const id = v || short || be;
    if (id) {
      if (!ids.includes(id)) ids.push(id);
      continue;
    }
    if (url.searchParams.get('list')) {
      playlist = true;
      continue;
    }
    invalid.push(line);
  }
  return { ids, invalid, playlist };
}

function sessionAnswer(ws: Workspace, session: Session, question: string): string {
  const ready = ws.videos.filter((v) => v.status === 'ready');
  if (!ready.length) {
    return 'The library is empty. Add a video first, then ask again. In strict mode I only answer from the workspace.';
  }
  const q = question.toLowerCase();
  const first = ready[0];
  const hasAttention = q.includes('attention') || q.includes('transformer') || q.includes('gpt') || q.includes('query');
  const hasCompare = q.includes('cnn') || q.includes('convolution') || q.includes('compare') || q.includes('difference');
  const hasSummary = q.includes('summar') || q.includes('five lines') || q.includes('overview');
  const hasDisagree = q.includes('disagree') || q.includes('claim') || q.includes('support');
  const cite = (videoId: string, start: number) => `[[cite:${videoId}:${start}]]`;
  const v2 = ready.find((v) => v.youtubeId === 'wjZofJX0v4M') ?? first;
  const v3 = ready.find((v) => v.youtubeId === 'iDulHoQ2F48') ?? ready[1] ?? first;
  const v4 = ready.find((v) => v.youtubeId === 'kCc8FmEb1nY') ?? ready[ready.length - 1];

  if (hasAttention) {
    return `Attention is a routing step. Each token produces a query, a key and a value. The query says what it is looking for, the key says what it offers, and the softmax over their dot products decides how much of each value to pull in. ${cite(v2.youtubeId, 341)} ${cite(v3.youtubeId, 521)}

That is why the operation is not a lookup. The model is not fetching a stored definition. It is deciding which earlier positions matter for this one. ${cite(v2.youtubeId, 181)}

Two details keep it stable: the dot products are scaled before the softmax, and each block has a residual connection around it. ${cite(v3.youtubeId, 761)}`;
  }
  if (hasCompare) {
    return `A convolution has a fixed neighborhood. A token at position 40 always looks at positions 39, 38, 37 in the same pattern. Attention learns the neighborhood per token. ${cite(v2.youtubeId, 701)}

The cost is different too. A convolution scales with the width of the kernel. Attention compares every position with every other position, so it grows quadratically with sequence length. ${cite(v3.youtubeId, 2601)}

That trade is the reason long-context work is mostly about making attention cheaper, not about adding more layers.`;
  }
  if (hasSummary) {
    return `1. A transformer predicts the next token from the tokens before it. ${cite(v2.youtubeId, 0)}
2. Attention lets each position gather information from earlier positions, and multiple heads track different relations. ${cite(v2.youtubeId, 701)}
3. The paper’s contribution is the architecture, not a new attention operation. ${cite(v3.youtubeId, 0)}
4. The cost is quadratic in sequence length, which is the design’s main trade. ${cite(v3.youtubeId, 2601)}
5. The knowledge lives in the weights, not in a database you can query. ${cite(v2.youtubeId, 1501)}`;
  }
  if (hasDisagree) {
    return `The paper is explicit about results and light on mechanism. It reports strong translation numbers and a general architecture, but it does not isolate why multi-head attention helps. ${cite(v3.youtubeId, 2301)}

The explainer goes further and says the pattern generalizes. That is a reasonable reading, but it is a claim about later work, not a result in the paper. ${cite(v3.youtubeId, 2001)}

The visual explainers are careful about this: they describe the mechanism and say the knowledge lives in the weights, not in a database. ${cite(v2.youtubeId, 1501)}`;
  }

  if (session.settings.grounding === 'strict') {
    return `These videos do not cover that. In strict mode I only answer from the workspace, and retrieval did not find a passage that supports an answer. Try a question about attention, the training loop, or the paper’s claims. Or switch this session to interpretive mode.`;
  }

  const persona =
    session.settings.personaId === 'skeptic'
      ? 'What the videos support first: '
      : session.settings.personaId === 'lecturer'
        ? 'Start with the operation. '
        : '';
  return `${persona}The workspace is about how transformers route information. The videos cover the mechanism, the training loop and the paper’s results, but they do not cover your exact question. ${cite(v2.youtubeId, 181)} ${cite(v3.youtubeId, 3001)}

Inference, marked as such: a useful next step is to ask a narrower question about one section, or add a source that addresses the missing piece. ${cite(v4.youtubeId, 1001)}`;
}

function extractCitations(content: string): Message['citations'] {
  const out: { videoId: string; start: number }[] = [];
  const re = /\[\[cite:([\w-]+):(\d+)\]\]/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(content))) {
    if (!out.some((c) => c.videoId === m![1] && c.start === +m![2])) {
      out.push({ videoId: m[1], start: +m[2] });
    }
  }
  return out;
}

function clone<T>(value: T): T {
  return structuredClone(value);
}

function assertSourceName(name: string): string {
  const base = name.replace(/\\/g, '/').split('/').pop()?.trim() || '';
  if (!base || base === '.' || base === '..') throw new ApiError('Give the source a file name.');
  if (!/\.(md|txt)$/i.test(base)) return `${base}.md`;
  return base;
}

function sourceVersion(content: string, note: string): SourceVersion {
  return { id: uid('ver'), ts: now(), content, note };
}

const api: Api = {
  auth: {
    async me() {
      await wait(60);
      const data = load();
      return data.users.find((u) => u.id === data.sessionUserId) ?? null;
    },
    async signIn(email, password) {
      await wait(280);
      const data = load();
      const user = data.users.find((u) => u.email.toLowerCase() === email.trim().toLowerCase());
      if (!user || data.passwords[user.id] !== password) {
        throw new ApiError('Email or password is wrong.', 401);
      }
      data.sessionUserId = user.id;
      save();
      return clone(user);
    },
    async signUp(name, email, password) {
      await wait(340);
      const data = load();
      const cleanEmail = email.trim().toLowerCase();
      if (!name.trim()) throw new ApiError('Add a display name.');
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cleanEmail)) throw new ApiError('That email does not look right.');
      if (password.length < 6) throw new ApiError('Use at least 6 characters for the password.');
      if (data.users.some((u) => u.email.toLowerCase() === cleanEmail)) {
        throw new ApiError('A profile already uses that email.', 409);
      }
      const user: User = { id: uid('u'), email: cleanEmail, name: name.trim(), createdAt: now() };
      data.users.push(user);
      data.passwords[user.id] = password;
      data.settings[user.id] = defaultLlm();
      data.sessionUserId = user.id;
      save();
      return clone(user);
    },
    async signOut() {
      await wait(120);
      const data = load();
      data.sessionUserId = null;
      save();
    },
    async demo() {
      await wait(260);
      const data = load();
      let user = data.users.find((u) => u.email === DEMO_EMAIL);
      if (!user) {
        user = demoUser;
        data.users.push(user);
        data.passwords[user.id] = DEMO_PASSWORD;
      }
      if (!data.settings[user.id]) data.settings[user.id] = defaultLlm();
      if (!data.workspaces.some((w) => w.ownerId === user!.id)) {
        data.workspaces.push(seedWorkspace(user.id));
      }
      data.sessionUserId = user.id;
      save();
      resumeJobs();
      return clone(user);
    },
  },

  workspaces: {
    async list() {
      await wait(90);
      const user = currentUser();
      return clone(
        load()
          .workspaces.filter((w) => w.ownerId === user.id)
          .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
      );
    },
    async get(id) {
      await wait(80);
      return clone(ownedWorkspace(id));
    },
    async create(name) {
      await wait(200);
      const user = currentUser();
      const clean = name.trim();
      if (!clean) throw new ApiError('Give the workspace a name.');
      const data = load();
      const ws: Workspace = {
        id: uid('ws'),
        ownerId: user.id,
        name: clean.slice(0, 80),
        slug: uniqueSlug(user.id, slugify(clean)),
        createdAt: now(),
        updatedAt: now(),
        settings: { useVisuals: false, summarize: false },
        videos: [],
        sessions: [],
        sources: [],
      };
      const session: Session = {
        id: uid('s'),
        title: 'First session',
        createdAt: now(),
        updatedAt: now(),
        settings: {
          grounding: 'strict',
          personaId: 'default',
          personaPrompt: null,
          modelOverride: null,
          useVisuals: false,
        },
        rollingSummary: '',
        messages: [],
      };
      ws.sessions.push(session);
      data.workspaces.push(ws);
      save();
      return clone(ws);
    },
    async rename(id, name) {
      await wait(150);
      const ws = ownedWorkspace(id);
      const clean = name.trim();
      if (!clean) throw new ApiError('The name cannot be empty.');
      ws.name = clean.slice(0, 80);
      ws.slug = uniqueSlug(ws.ownerId, slugify(clean), ws.id);
      touch(ws);
      save();
      return clone(ws);
    },
    async updateSettings(id, settings) {
      await wait(150);
      const ws = ownedWorkspace(id);
      ws.settings = { ...ws.settings, ...settings };
      touch(ws);
      save();
      return clone(ws);
    },
    async remove(id) {
      await wait(180);
      const ws = ownedWorkspace(id);
      const data = load();
      data.workspaces = data.workspaces.filter((w) => w.id !== ws.id);
      save();
      listeners.delete(id);
    },
  },

  videos: {
    async add(workspaceId, links) {
      await wait(240);
      const ws = ownedWorkspace(workspaceId);
      const { ids, invalid, playlist } = parseLinks(links);
      const added: Video[] = [];
      const skipped: string[] = [];
      const queue = [...ids];
      if (playlist) {
        ['wjZofJX0v4M', 'iDulHoQ2F48', 'kCc8FmEb1nY'].forEach((id) => {
          if (!queue.includes(id)) queue.push(id);
        });
      }
      queue.forEach((id) => {
        if (ws.videos.some((v) => v.youtubeId === id)) {
          skipped.push(id);
          return;
        }
        const v = makeVideo(id, `https://www.youtube.com/watch?v=${id}`);
        ws.videos.push(v);
        added.push(v);
        runJob(ws, v);
      });
      touch(ws);
      save();
      notify(ws.id);
      return { added: clone(added), skipped, invalid } satisfies AddLinksResult;
    },
    async retry(workspaceId, videoId) {
      await wait(120);
      const ws = ownedWorkspace(workspaceId);
      const v = ws.videos.find((x) => x.id === videoId);
      if (!v) throw new ApiError('Video not found.', 404);
      v.status = 'queued';
      v.error = null;
      runJob(ws, v);
      save();
      notify(ws.id);
    },
    async remove(workspaceId, videoId) {
      await wait(140);
      const ws = ownedWorkspace(workspaceId);
      clearTimers(videoId);
      ws.videos = ws.videos.filter((v) => v.id !== videoId);
      touch(ws);
      save();
      notify(ws.id);
    },
    async transcript(workspaceId) {
      await wait(120);
      const ws = ownedWorkspace(workspaceId);
      return demoTranscript(ws.videos);
    },
  },

  sessions: {
    async create(workspaceId, title) {
      await wait(160);
      const ws = ownedWorkspace(workspaceId);
      const session: Session = {
        id: uid('s'),
        title: title?.trim() || 'New session',
        createdAt: now(),
        updatedAt: now(),
        settings: {
          grounding: 'strict',
          personaId: 'default',
          personaPrompt: null,
          modelOverride: null,
          useVisuals: ws.settings.useVisuals,
        },
        rollingSummary: '',
        messages: [],
      };
      ws.sessions.push(session);
      touch(ws);
      save();
      notify(ws.id);
      return clone(session);
    },
    async update(workspaceId, sessionId, patch) {
      await wait(100);
      const ws = ownedWorkspace(workspaceId);
      const session = ws.sessions.find((s) => s.id === sessionId);
      if (!session) throw new ApiError('Session not found.', 404);
      if (patch.title !== undefined) session.title = patch.title.trim() || session.title;
      if (patch.settings) session.settings = { ...session.settings, ...patch.settings } as SessionSettings;
      session.updatedAt = now();
      touch(ws);
      save();
      notify(ws.id);
      return clone(session);
    },
    async remove(workspaceId, sessionId) {
      await wait(140);
      const ws = ownedWorkspace(workspaceId);
      ws.sessions = ws.sessions.filter((s) => s.id !== sessionId);
      touch(ws);
      save();
      notify(ws.id);
    },
    async send(workspaceId, sessionId, request: ChatRequest, onToken) {
      const ws = ownedWorkspace(workspaceId);
      const session = ws.sessions.find((s) => s.id === sessionId);
      if (!session) throw new ApiError('Session not found.', 404);
      const question = request.content.trim();
      if (!question) throw new ApiError('Write a question first.');

      const userMessage: Message = { id: uid('m'), role: 'user', content: question, ts: now() };
      session.messages.push(userMessage);
      if (session.messages.length === 1) {
        session.title = question.length > 42 ? `${question.slice(0, 42).trim()}…` : question;
      }
      session.updatedAt = now();
      touch(ws);
      save();
      notify(ws.id);

      const answer = sessionAnswer(ws, session, question);
      const chunks = answer.match(/\S+\s*/g) ?? [answer];
      let streamed = '';
      let stopped = false;
      for (const chunk of chunks) {
        if (request.signal?.aborted) {
          stopped = true;
          break;
        }
        streamed += chunk;
        onToken(chunk);
        await wait(14 + Math.random() * 18);
      }

      const assistant: Message = {
        id: uid('m'),
        role: 'assistant',
        content: streamed || answer,
        citations: extractCitations(streamed || answer),
        ts: now(),
        ...(stopped ? { error: 'Stopped by you.' } : {}),
      };
      session.messages.push(assistant);
      session.updatedAt = now();
      touch(ws);
      save();
      notify(ws.id);
      return clone(assistant);
    },
  },

  sources: {
    async create(workspaceId, name, content) {
      await wait(180);
      const ws = ownedWorkspace(workspaceId);
      const clean = assertSourceName(name);
      if (ws.sources.some((s) => s.name.toLowerCase() === clean.toLowerCase())) {
        throw new ApiError('A source with that name already exists.', 409);
      }
      const body = content ?? `# ${clean.replace(/\.(md|txt)$/i, '')}\n\n`;
      const doc: SourceDoc = {
        id: uid('src'),
        name: clean,
        content: body,
        updatedAt: now(),
        versions: [sourceVersion(body, 'Created')],
      };
      ws.sources.push(doc);
      touch(ws);
      save();
      notify(ws.id);
      return clone(doc);
    },
    async update(workspaceId, name, content, note) {
      await wait(160);
      const ws = ownedWorkspace(workspaceId);
      const doc = ws.sources.find((s) => s.name === name);
      if (!doc) throw new ApiError('Source not found.', 404);
      doc.content = content;
      doc.updatedAt = now();
      doc.versions.push(sourceVersion(content, note || 'Saved'));
      touch(ws);
      save();
      notify(ws.id);
      return clone(doc);
    },
    async remove(workspaceId, name) {
      await wait(140);
      const ws = ownedWorkspace(workspaceId);
      ws.sources = ws.sources.filter((s) => s.name !== name);
      touch(ws);
      save();
      notify(ws.id);
    },
    async restore(workspaceId, name, versionId) {
      await wait(180);
      const ws = ownedWorkspace(workspaceId);
      const doc = ws.sources.find((s) => s.name === name);
      if (!doc) throw new ApiError('Source not found.', 404);
      const version = doc.versions.find((v) => v.id === versionId);
      if (!version) throw new ApiError('Version not found.', 404);
      doc.content = version.content;
      doc.updatedAt = now();
      doc.versions.push(sourceVersion(version.content, `Restored from ${new Date(version.ts).toLocaleString()}`));
      touch(ws);
      save();
      notify(ws.id);
      return clone(doc);
    },
  },

  settings: {
    async get() {
      await wait(120);
      const user = currentUser();
      const data = load();
      const llm = data.settings[user.id] ?? defaultLlm();
      const app: AppSettings = {
        llm: clone(llm),
        root: site.root,
        version: site.version,
        doctor: [
          { label: 'Python', value: '3.12.4', ok: true },
          { label: 'ffmpeg', value: '7.0.2', ok: true },
          { label: 'yt-dlp', value: '2026.11.14', ok: true },
          { label: 'keyring', value: 'available', ok: true },
          {
            label: 'Whisper extra',
            value: 'not installed',
            ok: false,
            hint: 'pip install yt-gpt[whisper] only if a video has no captions.',
          },
        ],
      };
      return app;
    },
    async saveLlm(patch) {
      await wait(240);
      const user = currentUser();
      const data = load();
      const current = data.settings[user.id] ?? defaultLlm();
      const next: LlmSettings = { ...current, ...patch } as LlmSettings;
      if (patch.apiKey) {
        const key = patch.apiKey.trim();
        next.hasKey = key.length > 0;
        next.keyMasked = key.length >= 4 ? `•••• ${key.slice(-4)}` : '••••';
      }
      delete (next as LlmSettings & { apiKey?: string }).apiKey;
      data.settings[user.id] = next;
      save();
      return api.settings.get();
    },
    async testLlm() {
      await wait(720);
      const user = currentUser();
      const llm = load().settings[user.id] ?? defaultLlm();
      if (llm.provider === 'ollama') {
        return { ok: true, message: `Local endpoint answered at ${llm.baseUrl || 'http://localhost:11434'}.` };
      }
      if (!llm.hasKey) {
        return { ok: false, message: 'Add a key first, then test the connection.' };
      }
      return { ok: true, message: `${llm.model} answered in 640 ms. Vision, tools and prompt caching are available.` };
    },
    async rebuild() {
      await wait(900);
      return {
        ok: true,
        message: 'Demo rebuild complete. The real command rewrites clean.txt, chunks.jsonl and transcripts.md from segments.jsonl.',
      };
    },
  },

  events: {
    subscribe(workspaceId, listener) {
      const set = listeners.get(workspaceId) ?? new Set();
      set.add(listener);
      listeners.set(workspaceId, set);
      return () => set.delete(listener);
    },
  },
};

load();
resumeJobs();

export const mockApi = api;
