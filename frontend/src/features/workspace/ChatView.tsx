import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Markdown } from '../../components/Markdown';
import { Button } from '../../components/Button';
import { Icon } from '../../components/Icon';
import { SignalMeter } from '../../components/SignalMeter';
import { useToast } from '../../components/Toast';
import { suggestedQuestions, emptyState } from '../../data/site';
import { prefersReducedMotion } from '../../engine/env';
import { plural } from '../../lib/format';
import type { Message, Session, Workspace } from '../../types';

function timeOfDay(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit', hour12: false }).format(d);
}

function cleanForCopy(content: string) {
  return content
    .replace(/\[\[cite:[^\]]+\]\]/g, '')
    .replace(/\[[A-Za-z0-9_-]{6,} @ [\d:]+\]/g, '')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

function MessageItem({ message, videos }: { message: Message; videos: Workspace['videos'] }) {
  const { toast } = useToast();
  const isUser = message.role === 'user';
  const citations = message.citations?.length ?? 0;

  async function copy() {
    try {
      await navigator.clipboard.writeText(cleanForCopy(message.content));
      toast('Answer copied.');
    } catch {
      toast('The clipboard is not available.', 'fail');
    }
  }

  return (
    <article className={`msg msg--${message.role}`}>
      <div className="msg__head">
        <span className="msg__role">
          {isUser ? (
            'You'
          ) : (
            <>
              <span className="msg__dot" aria-hidden="true" />
              Answer
            </>
          )}
        </span>
        <span className="msg__time">{timeOfDay(message.ts)}</span>
      </div>
      {isUser ? (
        <p className="msg__user-text">{message.content}</p>
      ) : (
        <>
          <Markdown content={message.content} videos={videos} className="msg__prose" />
          {message.error && (
            <p className="msg__error" role="alert">
              {message.error}
            </p>
          )}
          <div className="msg__foot">
            <span className="msg__sources">
              {citations > 0 ? plural(citations, 'source') : 'No citation'}
            </span>
            <button type="button" className="msg__copy" onClick={copy} aria-label="Copy answer">
              <Icon name="copy" size={14} />
              Copy
            </button>
          </div>
        </>
      )}
    </article>
  );
}

export function ChatView({
  workspace,
  session,
  streaming,
  streamText,
  cooldown,
  onSend,
  onStop,
  onNewSession,
  onSelectSession,
  onOpenSettings,
}: {
  workspace: Workspace;
  session: Session | null;
  streaming: boolean;
  streamText: string;
  cooldown: number;
  onSend: (text: string) => void;
  onStop: () => void;
  onNewSession: () => void;
  onSelectSession: (id: string) => void;
  onOpenSettings: () => void;
}) {
  const [draft, setDraft] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastCount = useRef(0);

  const ready = workspace.videos.filter((v) => v.status === 'ready').length;
  const messages = session?.messages ?? [];

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    lastCount.current = 0;
    el.scrollTop = el.scrollHeight;
  }, [session?.id]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const count = messages.length;
    const isNew = count > lastCount.current;
    lastCount.current = count;
    if (isNew || count === 0) {
      el.scrollTo({ top: el.scrollHeight, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    }
  }, [messages.length]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !streaming) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < 220;
    if (near) el.scrollTop = el.scrollHeight;
  }, [streamText, streaming]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(180, el.scrollHeight)}px`;
  }, [draft]);

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const text = draft.trim();
    if (!text || streaming || cooldown > 0) return;
    setDraft('');
    onSend(text);
  }

  return (
    <section className="chat" aria-label="Conversation">
      <div className="chat__tabs">
        <div className="chat__tablist" role="tablist" aria-label="Sessions">
          {workspace.sessions.map((s) => (
            <button
              key={s.id}
              id={`session-tab-${s.id}`}
              type="button"
              role="tab"
              aria-selected={session?.id === s.id}
              aria-controls="chat-panel"
              className={`chat__tab${session?.id === s.id ? ' is-current' : ''}`}
              disabled={streaming && session?.id !== s.id}
              onClick={() => onSelectSession(s.id)}
            >
              <span className="chat__tab-title">{s.title}</span>
              <span className="chat__tab-count">{String(s.messages.length).padStart(2, '0')}</span>
            </button>
          ))}
        </div>
        <div className="chat__tab-actions">
          <button
            type="button"
            className="chat__tab-new"
            onClick={onNewSession}
            disabled={streaming}
            aria-label="New session"
            title="New session"
          >
            <Icon name="plus" size={16} />
          </button>
          <button
            type="button"
            className="chat__tab-new"
            onClick={onOpenSettings}
            aria-label="Session settings"
            title="Session settings"
          >
            <Icon name="settings" size={16} />
          </button>
        </div>
      </div>

      <div
        className="chat__scroll"
        ref={scrollRef}
        id="chat-panel"
        role="tabpanel"
        aria-labelledby={session ? `session-tab-${session.id}` : undefined}
        data-lenis-prevent
      >
        {messages.length === 0 && !streaming ? (
          <div className="chat-empty">
            <p className="eyebrow">Session</p>
            <h2 className="chat-empty__title">{emptyState.sessions.title}</h2>
            <p className="chat-empty__body">{emptyState.sessions.body}</p>
            <div className="chat-empty__meta">
              <SignalMeter bars={9} />
              <span>{plural(ready, 'source')} ready</span>
              {ready === 0 && <span>Add a video first</span>}
            </div>
            {ready > 0 ? (
              <div className="chat-empty__prompts" aria-label="Suggested questions">
                {suggestedQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="prompt"
                    onClick={() => onSend(q)}
                    disabled={streaming || cooldown > 0}
                  >
                    <span>{q}</span>
                    <Icon name="arrow-up-right" size={15} />
                  </button>
                ))}
              </div>
            ) : (
              <p className="chat-empty__hint">
                Paste a link in the library. Captions are fetched first, then the video becomes a source.
              </p>
            )}
          </div>
        ) : (
          <div className="chat__messages">
            {messages.map((m) => (
              <MessageItem key={m.id} message={m} videos={workspace.videos} />
            ))}
            {streaming && (
              <article className="msg msg--assistant msg--streaming" aria-busy="true">
                <div className="msg__head">
                  <span className="msg__role">
                    <span className="msg__dot msg__dot--live" aria-hidden="true" />
                    Answer
                  </span>
                  <span className="msg__time">streaming</span>
                </div>
                {streamText ? (
                  <Markdown content={streamText} videos={workspace.videos} className="msg__prose" />
                ) : (
                  <p className="stream-wait">
                    <SignalMeter bars={9} />
                    Reading the sources
                  </p>
                )}
                <span className="stream-caret" aria-hidden="true" />
              </article>
            )}
          </div>
        )}
      </div>

      <form className="composer" onSubmit={submit}>
        {cooldown > 0 && (
          <div className="composer__cooldown" role="status">
            <Icon name="clock" size={14} />
            <span className="sr-only">Rate limit cooldown active.</span>
            <span aria-hidden="true">
              Rate limit reached. Send again in <strong>{cooldown}s</strong>.
            </span>
          </div>
        )}
        <div className="composer__meta">
          <span>
            {streaming
              ? 'Answer in progress. Stop to edit.'
              : cooldown > 0
                ? `Cooling down for ${cooldown}s.`
                : ready > 0
                  ? `${plural(ready, 'source')} ready. Answers cite the minute.`
                  : 'No ready sources yet.'}
          </span>
          <span className="composer__key">Enter to send · Shift + Enter for a new line</span>
        </div>
        <div className="composer__box">
          <label className="sr-only" htmlFor="composer-input">
            Ask about these videos
          </label>
          <textarea
            ref={textareaRef}
            id="composer-input"
            className="composer__input"
            rows={2}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Ask about these videos"
            disabled={!session}
          />
          <div className="composer__actions">
            {streaming ? (
              <Button variant="outline" size="sm" icon="stop" onClick={onStop}>
                Stop
              </Button>
            ) : (
              <Button
                type="submit"
                size="sm"
                iconRight="send"
                disabled={!draft.trim() || !session || cooldown > 0}
              >
                Send
              </Button>
            )}
          </div>
        </div>
      </form>
    </section>
  );
}
