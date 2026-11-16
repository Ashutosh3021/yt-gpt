import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { api } from '../api';
import { useAsync } from '../hooks/useAsync';
import { useToast } from '../components/Toast';
import { PageMeta } from '../components/PageMeta';
import { GlobalTopbar } from '../components/GlobalTopbar';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { SourceBadge, Badge } from '../components/Chip';
import { LoadingPane, EmptyState } from '../components/States';
import { formatCount, formatMinutes, formatTime } from '../components/Timecode';
import { relativeTime, plural } from '../lib/format';
import { scrollToTarget } from '../engine';
import { ease, prefersReducedMotion } from '../engine/env';
import { transitionNavigate } from '../motion/navigate';
import { site } from '../data/site';

gsap.registerPlugin(ScrollTrigger);

function highlight(text: string, query: string): ReactNode {
  const q = query.trim();
  if (!q) return text;
  const lower = text.toLowerCase();
  const ql = q.toLowerCase();
  const out: ReactNode[] = [];
  let i = 0;
  let at = lower.indexOf(ql);
  if (at === -1) return text;
  while (at !== -1) {
    if (at > i) out.push(text.slice(i, at));
    out.push(<mark key={`${at}-${out.length}`}>{text.slice(at, at + q.length)}</mark>);
    i = at + q.length;
    at = lower.indexOf(ql, i);
  }
  if (i < text.length) out.push(text.slice(i));
  return out;
}

export function TranscriptPage() {
  const { wsId = '' } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: ws, loading, error } = useAsync(() => api.workspaces.get(wsId), [wsId]);
  const [query, setQuery] = useState('');
  const [activeId, setActiveId] = useState<string | null>(null);
  const rootRef = useRef<HTMLElement>(null);

  const readyVideos = useMemo(() => ws?.videos.filter((v) => v.status === 'ready') ?? [], [ws]);
  const tokens = useMemo(() => readyVideos.reduce((sum, v) => sum + v.tokens, 0), [readyVideos]);
  const pending = (ws?.videos.length ?? 0) - readyVideos.length;

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return 0;
    return readyVideos.reduce(
      (sum, v) =>
        sum + v.segments.reduce((n, s) => n + Math.max(0, s.text.toLowerCase().split(q).length - 1), 0),
      0,
    );
  }, [query, readyVideos]);

  useEffect(() => {
    if (!readyVideos.length) return;
    setActiveId((prev) => prev ?? readyVideos[0].id);
  }, [readyVideos]);

  useEffect(() => {
    if (!ws || prefersReducedMotion()) return;
    const root = rootRef.current;
    if (!root) return;
    const ctx = gsap.context(() => {
      gsap.from(root.querySelectorAll('.t-anim'), {
        y: 20,
        autoAlpha: 0,
        duration: 0.8,
        stagger: 0.07,
        ease: ease.out,
      });
      gsap.utils.toArray<HTMLElement>('.tsec').forEach((sec) => {
        gsap.from(sec, {
          y: 28,
          autoAlpha: 0,
          duration: 0.9,
          ease: ease.out,
          scrollTrigger: { trigger: sec, start: 'top 88%', once: true },
        });
      });
    }, root);
    return () => ctx.revert();
  }, [ws?.id]);

  useEffect(() => {
    if (!readyVideos.length) return;
    const sections = [...document.querySelectorAll<HTMLElement>('.tsec')];
    if (!sections.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActiveId((visible.target as HTMLElement).dataset.videoId ?? null);
      },
      { rootMargin: '-18% 0px -68% 0px', threshold: [0, 0.2, 0.6] },
    );
    sections.forEach((s) => io.observe(s));
    return () => io.disconnect();
  }, [readyVideos.length, ws?.id]);

  async function copyAll() {
    try {
      const text = await api.videos.transcript(wsId);
      await navigator.clipboard.writeText(text);
      toast('Transcript copied.');
    } catch {
      toast('The clipboard is not available.', 'fail');
    }
  }

  async function download() {
    try {
      const text = await api.videos.transcript(wsId);
      const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${ws?.slug ?? 'workspace'}-transcript.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast('Transcript downloaded.');
    } catch {
      toast('The transcript could not be written.', 'fail');
    }
  }

  function jump(id: string) {
    setActiveId(id);
    scrollToTarget(`#v-${id}`);
  }

  if (loading && !ws) {
    return (
      <>
        <PageMeta title="Transcript" description="Opening the transcript." />
        <GlobalTopbar page="Transcript" />
        <main id="main" className="transcript-boot" tabIndex={-1}>
          <LoadingPane label="Reading the transcript" />
        </main>
      </>
    );
  }

  if (!ws) {
    return (
      <>
        <PageMeta title="Transcript not found" description="This transcript is not in the local index." />
        <GlobalTopbar page="Transcript" />
        <main id="main" className="transcript" tabIndex={-1}>
          <EmptyState
            title="No transcript at this address."
            body={error || `The workspace may have moved, or it was deleted from ${site.root}.`}
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

  return (
    <>
      <PageMeta
        title={`${ws.name} transcript`}
        description={`The full transcript for ${ws.name}, with timecodes. ${plural(readyVideos.length, 'video')} ready to search.`}
        path={`/w/${ws.id}/transcript`}
      />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <GlobalTopbar
        page="Transcript"
        crumb={
          <>
            <Link to={`/w/${ws.id}`} className="crumb-link">
              {ws.name}
            </Link>
            <span className="crumb-sep" aria-hidden="true">
              /
            </span>
            <span>Transcript</span>
          </>
        }
      />
      <main id="main" className="transcript" tabIndex={-1} ref={rootRef}>
        <header className="transcript__head">
          <Link to={`/w/${ws.id}`} className="transcript__back t-anim">
            <Icon name="arrow-left" size={16} />
            Back to the conversation
          </Link>
          <div className="transcript__head-grid">
            <div>
              <p className="eyebrow t-anim">Transcript</p>
              <h1 className="transcript__title t-anim">{ws.name}</h1>
              <p className="transcript__lede t-anim">
                Every segment from the ready videos, with the minute attached. Timecodes open on YouTube.
              </p>
            </div>
            <div className="transcript__actions t-anim">
              <Button variant="outline" size="sm" icon="download" onClick={download}>
                Download .md
              </Button>
              <Button variant="quiet" size="sm" icon="copy" onClick={copyAll}>
                Copy all
              </Button>
            </div>
          </div>
          <div className="transcript__meta t-anim">
            <span>{plural(readyVideos.length, 'video')}</span>
            <span>{formatCount(tokens)} tokens</span>
            <span>updated {relativeTime(ws.updatedAt)}</span>
            {ws.demo && <Badge tone="neutral">sample data</Badge>}
          </div>
          {pending > 0 && (
            <p className="transcript__pending t-anim">
              <Icon name="clock" size={14} />
              {plural(pending, 'video')} still processing or failed.
              <Link to={`/w/${ws.id}`}>Open the library</Link>
            </p>
          )}
        </header>

        {readyVideos.length === 0 ? (
          <EmptyState
            className="transcript__empty"
            title="No transcript yet."
            body="Add a video with captions. The transcript appears here once the text is cleaned and indexed."
            action={
              <Button variant="outline" icon="library" onClick={() => transitionNavigate(navigate, `/w/${ws.id}`)}>
                Open the library
              </Button>
            }
          />
        ) : (
          <div className="transcript__grid">
            <nav className="transcript__index" aria-label="Videos in this transcript">
              <p className="transcript__index-label">Videos</p>
              <ol>
                {readyVideos.map((v, i) => (
                  <li key={v.id}>
                    <button
                      type="button"
                      className={`transcript__index-item${activeId === v.id ? ' is-current' : ''}`}
                      onClick={() => jump(v.id)}
                      aria-current={activeId === v.id ? 'true' : undefined}
                    >
                      <span className="transcript__index-num">{String(i + 1).padStart(2, '0')}</span>
                      <span className="transcript__index-title">{v.title}</span>
                      <span className="transcript__index-time">{formatMinutes(v.durationS)}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </nav>

            <div className="transcript__read">
              {readyVideos.map((v, i) => (
                <section
                  key={v.id}
                  className="tsec"
                  id={`v-${v.id}`}
                  data-video-id={v.id}
                  tabIndex={-1}
                  aria-labelledby={`v-title-${v.id}`}
                >
                  <header className="tsec__head">
                    <span className="tsec__index">{String(i + 1).padStart(2, '0')}</span>
                    <div className="tsec__id">
                      <h2 id={`v-title-${v.id}`} className="tsec__title">
                        {v.title}
                      </h2>
                      <p className="tsec__meta">
                        <span>{v.channel}</span>
                        <span>{formatMinutes(v.durationS)}</span>
                        <SourceBadge source={v.transcriptSource} />
                      </p>
                    </div>
                    <a href={v.url} target="_blank" rel="noopener noreferrer" className="tsec__watch">
                      Watch
                      <Icon name="external" size={14} />
                    </a>
                  </header>
                  <div className="tsec__segments">
                    {v.segments.map((s, idx) => (
                      <p
                        key={`${v.id}-${idx}`}
                        className={`tseg${query.trim() && s.text.toLowerCase().includes(query.trim().toLowerCase()) ? ' is-hit' : ''}`}
                      >
                        <a
                          className="tseg__tc"
                          href={`https://youtu.be/${v.youtubeId}?t=${s.start}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Open ${formatTime(s.start)} on YouTube`}
                        >
                          {formatTime(s.start)}
                        </a>
                        <span className="tseg__text">{highlight(s.text, query)}</span>
                      </p>
                    ))}
                  </div>
                </section>
              ))}
            </div>

            <aside className="transcript__margin" aria-label="Transcript tools">
              <div className="transcript__find">
                <label htmlFor="transcript-search" className="transcript__find-label">
                  Find a phrase
                </label>
                <div className="transcript__find-box">
                  <Icon name="search" size={16} />
                  <input
                    id="transcript-search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key !== 'Enter') return;
                      const mark = rootRef.current?.querySelector('mark');
                      if (mark) scrollToTarget(mark as HTMLElement);
                    }}
                    placeholder="softmax, residual, ..."
                    autoComplete="off"
                  />
                  {query && (
                    <button
                      type="button"
                      className="transcript__find-clear"
                      aria-label="Clear search"
                      onClick={() => setQuery('')}
                    >
                      <Icon name="x" size={14} />
                    </button>
                  )}
                </div>
                <p className="transcript__find-count" aria-live="polite">
                  {query.trim()
                    ? matches === 0
                      ? 'No matches in the ready videos.'
                      : `${matches} ${matches === 1 ? 'match' : 'matches'}`
                    : 'Search the text. Press Enter to jump.'}
                </p>
              </div>
              <div className="transcript__note">
                <p>
                  Captions can be wrong at names and numbers. The timecode is the check: it opens the exact
                  second.
                </p>
              </div>
              <Button variant="outline" size="sm" block icon="copy" onClick={copyAll}>
                Copy all
              </Button>
            </aside>
          </div>
        )}
      </main>
    </>
  );
}
