import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { api } from '../api';
import { useAsync } from '../hooks/useAsync';
import { useToast } from '../components/Toast';
import { PageMeta } from '../components/PageMeta';
import { GlobalTopbar } from '../components/GlobalTopbar';
import { Button } from '../components/Button';
import { Badge } from '../components/Chip';
import { Icon } from '../components/Icon';
import { Popover } from '../components/Popover';
import { Dialog } from '../components/Dialog';
import { FormError } from '../components/Field';
import { LoadingPane, EmptyState } from '../components/States';
import { transitionNavigate } from '../motion/navigate';
import { ease, prefersReducedMotion } from '../engine/env';
import { relativeTime, plural } from '../lib/format';
import { site, emptyState } from '../data/site';
import type { Workspace } from '../types';

function VideoStrip({ workspace }: { workspace: Workspace }) {
  const videos = workspace.videos;
  return (
    <span className="vstrip" aria-hidden="true">
      {videos.length === 0 && <span className="vstrip__empty" />}
      {videos.map((v) => (
        <span
          key={v.id}
          className={`vstrip__tick vstrip__tick--${v.status}`}
          style={{ flexGrow: Math.max(1, Math.round(v.durationS / 60)) }}
        />
      ))}
    </span>
  );
}

export function DashboardPage() {
  const { data, error, loading, reload } = useAsync(() => api.workspaces.list(), []);
  const navigate = useNavigate();
  const { toast } = useToast();
  const listRef = useRef<HTMLUListElement>(null);
  const animated = useRef(false);
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [renameTarget, setRenameTarget] = useState<Workspace | null>(null);
  const [renameName, setRenameName] = useState('');
  const [renameError, setRenameError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Workspace | null>(null);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    if (!data || animated.current || prefersReducedMotion()) return;
    const root = listRef.current;
    if (!root) return;
    const rows = root.querySelectorAll('.ws-row');
    if (!rows.length) return;
    animated.current = true;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        rows,
        { y: 22, autoAlpha: 0 },
        { y: 0, autoAlpha: 1, duration: 0.8, stagger: 0.06, ease: ease.out, delay: 0.08 },
      );
    }, root);
    return () => ctx.revert();
  }, [data]);

  async function createWorkspace(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setCreateError('Give the workspace a name.');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const ws = await api.workspaces.create(name.trim());
      setName('');
      await transitionNavigate(navigate, `/w/${ws.id}`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'The workspace could not be created.');
      setCreating(false);
    }
  }

  async function saveRename() {
    if (!renameTarget) return;
    if (!renameName.trim()) {
      setRenameError('The name cannot be empty.');
      return;
    }
    try {
      await api.workspaces.rename(renameTarget.id, renameName.trim());
      setRenameTarget(null);
      reload();
      toast('Workspace renamed.');
    } catch (err) {
      setRenameError(err instanceof Error ? err.message : 'The rename did not save.');
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setRemoving(true);
    try {
      await api.workspaces.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
      toast('Workspace removed. The files are in the trash.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The workspace could not be removed.', 'fail');
    } finally {
      setRemoving(false);
    }
  }

  return (
    <>
      <PageMeta
        title="Workspaces"
        description="Your local yt-gpt workspaces. Each one holds videos, sessions and sources. Open a workspace to ask questions with timecoded citations."
        path="/app"
      />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <GlobalTopbar page="Workspaces" />
      <main id="main" className="dash" tabIndex={-1}>
        <section className="dash__intro">
          <p className="eyebrow" data-reveal="fade" data-intro>
            The desk
          </p>
          <h1 className="dash__title" data-split="lines" data-intro>
            Workspaces
            <span className="dash__title-sub">for questions with a timestamp.</span>
          </h1>
          <p className="dash__lede" data-reveal="up" data-intro data-delay="0.1">
            Each workspace is a folder of videos, transcripts and notes. Open one to ask the room, or start
            with a question and add the sources that answer it.
          </p>

          <div className="dash__create" data-reveal="up" data-intro data-delay="0.16">
            <label className="dash__create-label" htmlFor="new-workspace">
              New workspace
            </label>
            <form className="dash__create-form" onSubmit={createWorkspace}>
              <input
                id="new-workspace"
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="The attention mechanism"
                autoComplete="off"
              />
              <Button type="submit" icon="plus" loading={creating}>
                Create
              </Button>
            </form>
            {createError && <FormError>{createError}</FormError>}
          </div>

          <div className="dash__note" data-reveal="fade" data-intro data-delay="0.22">
            <Icon name="database" size={18} />
            <p>
              Files live in <code>{site.root}</code>. Nothing syncs unless you add a provider in settings.
            </p>
          </div>
        </section>

        <section className="dash__list-wrap" aria-labelledby="dash-list-title">
          <div className="dash__list-head">
            <h2 id="dash-list-title" className="dash__list-title">
              Open a workspace
            </h2>
            <span className="dash__count">
              {data ? plural(data.length, 'workspace') : '—'}
            </span>
          </div>

          {loading && !data && <LoadingPane label="Reading the local index" />}
          {error && (
            <div className="dash__error" role="alert">
              <p>{error}</p>
              <Button variant="outline" size="sm" icon="retry" onClick={reload}>
                Try again
              </Button>
            </div>
          )}

          {data && data.length === 0 && (
            <EmptyState
              title={emptyState.workspaces.title}
              body={emptyState.workspaces.body}
              action={
                <Button variant="outline" size="sm" icon="plus" onClick={() => document.getElementById('new-workspace')?.focus()}>
                  Name the first one
                </Button>
              }
            />
          )}

          {data && data.length > 0 && (
            <ul className="dash__list" ref={listRef}>
              {data.map((ws, i) => {
                const ready = ws.videos.filter((v) => v.status === 'ready').length;
                return (
                  <li key={ws.id} className="ws-row">
                    <Link className="ws-row__link" to={`/w/${ws.id}`} data-cursor="Open">
                      <span className="ws-row__index">{String(i + 1).padStart(2, '0')}</span>
                      <span className="ws-row__body">
                        <span className="ws-row__top">
                          <span className="ws-row__name">{ws.name}</span>
                          {ws.demo && <Badge tone="neutral">sample</Badge>}
                        </span>
                        <span className="ws-row__meta">
                          <span>
                            {plural(ws.videos.length, 'video')}, {ready} ready
                          </span>
                          <span>{plural(ws.sessions.length, 'session')}</span>
                          <span>edited {relativeTime(ws.updatedAt)}</span>
                        </span>
                        <VideoStrip workspace={ws} />
                      </span>
                      <Icon name="arrow-up-right" size={20} className="ws-row__arrow" />
                    </Link>
                    <div className="ws-row__menu">
                      <Popover
                        label={`Actions for ${ws.name}`}
                        trigger={<Icon name="more" size={18} />}
                        triggerClassName="popover__trigger--icon"
                        panelClassName="menu-panel"
                      >
                        {(close) => (
                          <>
                            <button
                              type="button"
                              className="menu-item"
                              onClick={() => {
                                close();
                                setRenameTarget(ws);
                                setRenameName(ws.name);
                                setRenameError(null);
                              }}
                            >
                              <Icon name="edit" size={16} />
                              Rename
                            </button>
                            <button
                              type="button"
                              className="menu-item menu-item--danger"
                              onClick={() => {
                                close();
                                setDeleteTarget(ws);
                              }}
                            >
                              <Icon name="trash" size={16} />
                              Delete
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

          <footer className="dash__foot">
            <span>yt-gpt {site.version}</span>
            <span>{site.storagePath}</span>
          </footer>
        </section>
      </main>

      <Dialog
        open={!!renameTarget}
        title="Rename workspace"
        description="The folder name changes. The videos and sessions stay in place."
        onClose={() => setRenameTarget(null)}
        footer={
          <>
            <Button variant="quiet" onClick={() => setRenameTarget(null)}>
              Cancel
            </Button>
            <Button onClick={saveRename}>Save name</Button>
          </>
        }
      >
        <label className="field__label" htmlFor="rename-workspace">
          Name
        </label>
        <input
          id="rename-workspace"
          className="input"
          value={renameName}
          onChange={(e) => setRenameName(e.target.value)}
          data-autofocus
        />
        {renameError && <FormError>{renameError}</FormError>}
      </Dialog>

      <Dialog
        open={!!deleteTarget}
        title="Delete this workspace?"
        description={`“${deleteTarget?.name ?? ''}” and its videos, sessions and sources move to the trash. You can restore the folder from ${site.root}.`}
        onClose={() => setDeleteTarget(null)}
        footer={
          <>
            <Button variant="quiet" onClick={() => setDeleteTarget(null)}>
              Keep it
            </Button>
            <Button variant="danger" loading={removing} onClick={confirmDelete}>
              Delete workspace
            </Button>
          </>
        }
      />
    </>
  );
}
