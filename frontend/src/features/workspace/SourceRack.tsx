import { useRef, useState, type FormEvent } from 'react';
import { api } from '../../api';
import { useToast } from '../../components/Toast';
import { Button } from '../../components/Button';
import { StatusChip, SourceBadge } from '../../components/Chip';
import { Icon } from '../../components/Icon';
import { Popover } from '../../components/Popover';
import { Dialog } from '../../components/Dialog';
import { FormError } from '../../components/Field';
import { formatCount, formatMinutes } from '../../components/Timecode';
import { emptyState } from '../../data/site';
import type { Video, Workspace } from '../../types';

export function SourceRack({
  workspace,
  selectedId,
  onSelect,
  onChanged,
  embedded = false,
}: {
  workspace: Workspace;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onChanged: () => void;
  embedded?: boolean;
}) {
  const { toast } = useToast();
  const [links, setLinks] = useState('');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [removeTarget, setRemoveTarget] = useState<Video | null>(null);
  const [removing, setRemoving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const videos = workspace.videos;
  const ready = videos.filter((v) => v.status === 'ready').length;
  const totalTokens = videos.reduce((sum, v) => sum + v.tokens, 0);

  async function addLinks(e: FormEvent) {
    e.preventDefault();
    if (!links.trim()) {
      setError('Paste at least one link.');
      return;
    }
    setAdding(true);
    setError(null);
    try {
      const result = await api.videos.add(workspace.id, links);
      setLinks('');
      onChanged();
      if (result.added[0]) onSelect(result.added[0].id);
      const parts: string[] = [];
      if (result.added.length) parts.push(`${result.added.length} added`);
      if (result.skipped.length) parts.push(`${result.skipped.length} already here`);
      if (result.invalid.length) parts.push(`${result.invalid.length} unreadable`);
      toast(parts.join(' · ') || 'Nothing to add.', result.invalid.length ? 'signal' : 'neutral');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Those links could not be added.');
    } finally {
      setAdding(false);
    }
  }

  async function retry(video: Video) {
    try {
      await api.videos.retry(workspace.id, video.id);
      onChanged();
      toast('Fetching the captions again.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The retry did not start.', 'fail');
    }
  }

  async function remove() {
    if (!removeTarget) return;
    setRemoving(true);
    try {
      await api.videos.remove(workspace.id, removeTarget.id);
      if (selectedId === removeTarget.id) onSelect('');
      setRemoveTarget(null);
      onChanged();
      toast('Video removed from the library.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The video could not be removed.', 'fail');
    } finally {
      setRemoving(false);
    }
  }

  async function download() {
    try {
      const text = await api.videos.transcript(workspace.id);
      const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `${workspace.slug}-transcript.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast('Transcript downloaded.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The transcript could not be written.', 'fail');
    }
  }

  return (
    <div className={`rack${embedded ? ' rack--embedded' : ''}`}>
      {!embedded && (
        <div className="rack__head">
          <div>
            <p className="eyebrow eyebrow--light">Library</p>
            <h2 className="rack__title">
              Sources <span className="rack__count">{String(videos.length).padStart(2, '0')}</span>
            </h2>
          </div>
          <button
            type="button"
            className="rack__add-btn"
            aria-label="Add links to the library"
            onClick={() => textareaRef.current?.focus()}
          >
            <Icon name="plus" size={18} />
          </button>
        </div>
      )}

      {videos.length === 0 ? (
        <div className="rack__empty">
          <p className="rack__empty-title">{emptyState.videos.title}</p>
          <p>{emptyState.videos.body}</p>
        </div>
      ) : (
        <ul className="rack__list" data-lenis-prevent>
          {videos.map((v) => {
            const busy = v.status !== 'ready' && v.status !== 'failed';
            return (
              <li
                key={v.id}
                className={`vrow${selectedId === v.id ? ' is-selected' : ''}${v.status === 'failed' ? ' is-failed' : ''}${busy ? ' is-busy' : ''}`}
                data-video-row={v.id}
              >
                <button
                  type="button"
                  className="vrow__main"
                  aria-pressed={selectedId === v.id}
                  onClick={() => onSelect(v.id)}
                >
                  <span className="vrow__top">
                    <span className="vrow__title">{v.title}</span>
                    <StatusChip status={v.status} dense />
                  </span>
                  <span className="vrow__meta">
                    <span className="vrow__channel">{v.channel}</span>
                    <span>{formatMinutes(v.durationS)}</span>
                  </span>
                  {v.status === 'failed' ? (
                    <span className="vrow__error">
                      <Icon name="alert" size={13} />
                      {v.error || 'The captions could not be fetched.'}
                    </span>
                  ) : (
                    <span className="vrow__meta vrow__meta--sub">
                      <SourceBadge source={v.transcriptSource} />
                      <span>{formatCount(v.tokens)} tokens</span>
                    </span>
                  )}
                </button>
                <span className="vrow__port" data-port aria-hidden="true">
                  <span />
                </span>
                <div className="vrow__menu">
                  <Popover
                    label={`Actions for ${v.title}`}
                    trigger={<Icon name="more" size={17} />}
                    triggerClassName="popover__trigger--icon"
                    panelClassName="menu-panel"
                  >
                    {(close) => (
                      <>
                        {v.status === 'failed' && (
                          <button
                            type="button"
                            className="menu-item"
                            onClick={() => {
                              close();
                              void retry(v);
                            }}
                          >
                            <Icon name="retry" size={16} />
                            Retry fetch
                          </button>
                        )}
                        <button
                          type="button"
                          className="menu-item menu-item--danger"
                          onClick={() => {
                            close();
                            setRemoveTarget(v);
                          }}
                        >
                          <Icon name="trash" size={16} />
                          Remove
                        </button>
                      </>
                    )}
                  </Popover>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <form className="rack__add" onSubmit={addLinks}>
        <div className="rack__add-top">
          <label className="rack__label" htmlFor={`links-${embedded ? 'drawer' : 'rail'}`}>
            Add links
          </label>
          <span className="rack__hint">One per line</span>
        </div>
        <textarea
          ref={textareaRef}
          id={`links-${embedded ? 'drawer' : 'rail'}`}
          className="rack__textarea"
          rows={3}
          value={links}
          onChange={(e) => setLinks(e.target.value)}
          placeholder={'https://youtu.be/...\nhttps://www.youtube.com/playlist?list=...'}
          spellCheck={false}
        />
        {error && <FormError>{error}</FormError>}
        <Button type="submit" size="sm" variant="outline" block icon="plus" loading={adding}>
          Add to library
        </Button>
      </form>

      <footer className="rack__foot">
        <span className="rack__stat">
          {ready} ready · {formatCount(totalTokens)} tokens
        </span>
        <button type="button" className="rack__export" onClick={download} disabled={!videos.length}>
          <Icon name="download" size={14} />
          Export .md
        </button>
      </footer>

      <Dialog
        open={!!removeTarget}
        title="Remove this video?"
        description={`“${removeTarget?.title ?? ''}” leaves the library. Its transcript, chunks and citations are deleted. The original video stays on YouTube.`}
        onClose={() => setRemoveTarget(null)}
        footer={
          <>
            <Button variant="quiet" onClick={() => setRemoveTarget(null)}>
              Keep it
            </Button>
            <Button variant="danger" loading={removing} onClick={remove}>
              Remove video
            </Button>
          </>
        }
      />
    </div>
  );
}
