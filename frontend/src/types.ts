export type VideoStatus =
  | 'queued'
  | 'fetching'
  | 'transcribing'
  | 'cleaning'
  | 'indexing'
  | 'ready'
  | 'failed';

export type TranscriptSource = 'manual' | 'auto' | 'whisper';
export type Grounding = 'strict' | 'interpretive';
export type PersonaId = 'default' | 'skeptic' | 'lecturer' | 'editor' | 'custom';

export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export interface Segment {
  start: number;
  end: number;
  text: string;
}

export interface Video {
  id: string;
  youtubeId: string;
  url: string;
  title: string;
  channel: string;
  durationS: number;
  language: string;
  transcriptSource: TranscriptSource;
  status: VideoStatus;
  error: string | null;
  addedAt: string;
  tokens: number;
  summary: string;
  segments: Segment[];
  visual: { enabled: boolean; status: 'none' | 'queued' | 'ready' | 'failed'; frames: number };
  demo?: boolean;
}

export interface Citation {
  videoId: string;
  start: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  ts: string;
  error?: string;
}

export interface SessionSettings {
  grounding: Grounding;
  personaId: PersonaId;
  personaPrompt: string | null;
  modelOverride: string | null;
  useVisuals: boolean;
}

export interface Session {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  settings: SessionSettings;
  rollingSummary: string;
  messages: Message[];
}

export interface SourceVersion {
  id: string;
  ts: string;
  content: string;
  note: string;
}

export interface SourceDoc {
  id: string;
  name: string;
  content: string;
  updatedAt: string;
  versions: SourceVersion[];
}

export interface Workspace {
  id: string;
  ownerId: string;
  name: string;
  slug: string;
  createdAt: string;
  updatedAt: string;
  settings: { useVisuals: boolean; summarize: boolean };
  videos: Video[];
  sessions: Session[];
  sources: SourceDoc[];
  demo?: boolean;
}

export interface LlmSettings {
  provider: 'openai' | 'anthropic' | 'google' | 'openrouter' | 'ollama' | 'custom';
  baseUrl: string;
  model: string;
  embeddingModel: string;
  hasKey: boolean;
  keyMasked: string;
  capabilities: { vision: boolean; tools: boolean; caching: boolean; contextK: number };
}

export interface DoctorCheck {
  label: string;
  value: string;
  ok: boolean;
  hint?: string;
}

export interface AddLinksResult {
  added: Video[];
  skipped: string[];
  invalid: string[];
}

export interface AppSettings {
  llm: LlmSettings;
  root: string;
  version: string;
  doctor: DoctorCheck[];
}

export interface ChatRequest {
  content: string;
  signal?: AbortSignal;
}

export interface Api {
  auth: {
    me(): Promise<User | null>;
    signIn(email: string, password: string): Promise<User>;
    signUp(name: string, email: string, password: string): Promise<User>;
    signOut(): Promise<void>;
    demo(): Promise<User>;
  };
  workspaces: {
    list(): Promise<Workspace[]>;
    get(id: string): Promise<Workspace>;
    create(name: string): Promise<Workspace>;
    rename(id: string, name: string): Promise<Workspace>;
    remove(id: string): Promise<void>;
  };
  videos: {
    add(workspaceId: string, links: string): Promise<AddLinksResult>;
    retry(workspaceId: string, videoId: string): Promise<void>;
    remove(workspaceId: string, videoId: string): Promise<void>;
    transcript(workspaceId: string): Promise<string>;
  };
  sessions: {
    create(workspaceId: string, title?: string): Promise<Session>;
    update(
      workspaceId: string,
      sessionId: string,
      patch: Partial<Pick<Session, 'title'>> & { settings?: Partial<SessionSettings> },
    ): Promise<Session>;
    remove(workspaceId: string, sessionId: string): Promise<void>;
    send(
      workspaceId: string,
      sessionId: string,
      request: ChatRequest,
      onToken: (text: string) => void,
    ): Promise<Message>;
  };
  sources: {
    create(workspaceId: string, name: string, content?: string): Promise<SourceDoc>;
    update(workspaceId: string, name: string, content: string, note?: string): Promise<SourceDoc>;
    remove(workspaceId: string, name: string): Promise<void>;
    restore(workspaceId: string, name: string, versionId: string): Promise<SourceDoc>;
  };
  settings: {
    get(): Promise<AppSettings>;
    saveLlm(patch: Partial<LlmSettings> & { apiKey?: string }): Promise<AppSettings>;
    testLlm(): Promise<{ ok: boolean; message: string }>;
    rebuild(): Promise<{ ok: boolean; message: string }>;
  };
  events: {
    subscribe(workspaceId: string, listener: () => void): () => void;
  };
}
