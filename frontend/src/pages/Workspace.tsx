import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAsync } from '../hooks/useAsync';
import { useToast } from '../components/Toast';
import { PageMeta } from '../components/PageMeta';
import { Wordmark } from '../components/Wordmark';
import { GlobalTopbar } from '../components/GlobalTopbar';
import { Drawer } from '../components/Drawer';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { LoadingPane, EmptyState } from '../components/States';
import { transitionNavigate } from '../motion/navigate';
import { WorkspaceTopbar } from '../features/workspace/WorkspaceTopbar';
import { SourceRack } from '../features/workspace/SourceRack';
import { ChatView } from '../features/workspace/ChatView';
import { SourcesPanel } from '../features/workspace/SourcesPanel';
import { SessionSettings } from '../features/workspace/SessionSettings';
import { site } from '../data/site';

export function WorkspacePage() {
  const { wsId = '' } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: ws, error, loading, reload, setData } = useAsync(() => api.workspaces.get(wsId), [wsId]);
  const { data: app } = useAsync(() => api.settings.get(), []);
  const { data: allWs, reload: reloadAll } = useAsync(() => api.workspaces.list(), []);
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [drawer, setDrawer] = useState<'library' | 'sources' | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const streamingRef = useRef(false);

  const sessionParam = searchParams.get('session');
  const sessions = ws?.sessions ?? [];
  const session = sessions.find((s) => s.id === sessionParam) ?? sessions[0] ?? null;

  useEffect(() => {
    streamingRef.current = streaming;
  }, [streaming]);

  useEffect(() => {
    if (!ws) return;
    setSelectedVideo((prev) => {
      if (prev && ws.videos.some((v) => v.id === prev)) return prev;
      return ws.videos.find((v) => v.status === 'ready')?.id ?? ws.videos[0]?.id ?? null;
    });
  }, [ws?.id, ws?.videos.length]);

  useEffect(() => {
    if (!wsId) return;
    return api.events.subscribe(wsId, () => {
      if (streamingRef.current) return;
      reload();
      reloadAll();
    });
  }, [wsId, reload, reloadAll]);

  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  async function send(text: string) {
    if (!ws || !session || streaming) return;
    const sid = session.id;
    const controller = new AbortController();
    abortRef.current = controller;
    streamingRef.current = true;
    setStreaming(true);
    setStreamText('');
    setData((prev) =>
      prev
        ? {
            ...prev,
            sessions: prev.sessions.map((s) =>
              s.id === sid
                ? {
                    ...s,
                    messages: [
                      ...s.messages,
                      {
                        id: `tmp_${Date.now()}`,
                        role: 'user' as const,
                        content: text,
                        ts: new Date().toISOString(),
                      },
                    ],
                  }
                : s,
            ),
          }
        : prev,
    );
    try {
      const message = await api.sessions.send(ws.id, sid, { content: text, signal: controller.signal }, (token) =>
        setStreamText((prev) => prev + token),
      );
      if (message.error) toast(message.error, 'signal');
      setData((prev) =>
        prev
          ? {
              ...prev,
              sessions: prev.sessions.map((s) =>
                s.id === sid ? { ...s, messages: [...s.messages, message] } : s,
              ),
            }
          : prev,
      );
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The answer stopped.', 'fail');
    } finally {
      abortRef.current = null;
      setStreaming(false);
      streamingRef.current = false;
      setStreamText('');
      reload();
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  async function newSession() {
    if (!ws || streaming) return;
    try {
      const created = await api.sessions.create(ws.id);
      await reload();
      setSearchParams({ session: created.id }, { replace: true });
    } catch (err) {
      toast(err instanceof Error ? err.message : 'A new session could not be started.', 'fail');
    }
  }

  function selectSession(id: string) {
    setSearchParams({ session: id }, { replace: true });
  }

  if (loading && !ws) {
    return (
      <>
        <PageMeta title="Workspace" description="Opening a local workspace." />
        <main id="main" className="workspace-boot" tabIndex={-1}>
          <Wordmark asLink={false} />
          <LoadingPane label="Opening the workspace" />
        </main>
      </>
    );
  }

  if (!ws) {
    return (
      <>
        <PageMeta title="Workspace not found" description="This workspace is not in the local index." />
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <GlobalTopbar page="Workspace" />
        <main id="main" className="dash" tabIndex={-1}>
          <EmptyState
            className="dash__missing"
            title="This workspace is not here."
            body={error || `The folder may have moved, or it was deleted from ${site.root}.`}
            action={
              <Button variant="outline" icon="arrow-left" onClick={() => transitionNavigate(navigate, '/app')}>
                All workspaces
              </Button>
            }
          />
        </main>
      </>
    );
  }

  const modelLabel = session?.settings.modelOverride || app?.llm.model || 'default model';
  const grounding = session?.settings.grounding ?? 'strict';
  const switcher = allWs?.some((w) => w.id === ws.id) ? allWs : [ws, ...(allWs ?? [])];

  return (
    <>
      <PageMeta
        title={ws.name}
        description={`${ws.name} is a local yt-gpt workspace with ${ws.videos.length} videos and ${ws.sessions.length} sessions. Ask questions and get timecoded citations.`}
        path={`/w/${ws.id}`}
      />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="workspace">
        <WorkspaceTopbar
          workspace={ws}
          workspaces={switcher}
          grounding={grounding}
          modelLabel={modelLabel}
          onOpenLibrary={() => setDrawer('library')}
          onOpenSources={() => setDrawer('sources')}
          onOpenSettings={() => setSettingsOpen(true)}
        />
        <main id="main" className="workspace__body" tabIndex={-1}>
          <h1 className="sr-only">{ws.name}</h1>
          <aside className="workspace__rail" aria-label="Library">
            <SourceRack
              workspace={ws}
              selectedId={selectedVideo}
              onSelect={setSelectedVideo}
              onChanged={reload}
            />
          </aside>
          <ChatView
            workspace={ws}
            session={session}
            streaming={streaming}
            streamText={streamText}
            onSend={send}
            onStop={stop}
            onNewSession={newSession}
            onSelectSession={selectSession}
            onOpenSettings={() => setSettingsOpen(true)}
          />
          <aside className="workspace__folio" aria-label="Sources">
            <SourcesPanel workspace={ws} onChanged={reload} />
          </aside>
        </main>

        <svg id="signal-layer" className="signal-layer" aria-hidden="true" focusable="false" />
        <div id="source-card" className="source-card" aria-hidden="true">
          <div className="source-card__head">
            <span className="source-card__index" data-card-index>
              01
            </span>
            <span className="source-card__time" data-card-time>
              00:00
            </span>
            <span className="source-card__label">source</span>
          </div>
          <p className="source-card__title" data-card-title />
          <p className="source-card__snippet" data-card-snippet />
          <span className="source-card__hint">
            Open on YouTube
            <Icon name="arrow-up-right" size={13} />
          </span>
        </div>
      </div>

      <Drawer open={drawer === 'library'} onClose={() => setDrawer(null)} title="Library" eyebrow={ws.name}>
        <SourceRack
          workspace={ws}
          selectedId={selectedVideo}
          onSelect={(id) => {
            setSelectedVideo(id);
            setDrawer(null);
          }}
          onChanged={reload}
          embedded
        />
      </Drawer>

      <Drawer open={drawer === 'sources'} onClose={() => setDrawer(null)} title="Sources" eyebrow={ws.name}>
        <SourcesPanel workspace={ws} onChanged={reload} embedded />
      </Drawer>

      <SessionSettings
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        workspace={ws}
        session={session}
        onChanged={reload}
      />
    </>
  );
}
