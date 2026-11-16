import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react';
import { api } from '../../api';
import { useToast } from '../../components/Toast';
import { Button } from '../../components/Button';
import { Icon } from '../../components/Icon';
import { Popover } from '../../components/Popover';
import { Dialog } from '../../components/Dialog';
import { FormError } from '../../components/Field';
import { Markdown } from '../../components/Markdown';
import { EmptyState } from '../../components/States';
import { relativeTime } from '../../lib/format';
import { emptyState } from '../../data/site';
import type { SourceDoc, Workspace } from '../../types';

type View = { mode: 'list' } | { mode: 'edit'; name: string } | { mode: 'history'; name: string };

function stamp(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(d);
}

export function SourcesPanel({
  workspace,
  onChanged,
  embedded = false,
}: {
  workspace: Workspace;
  onChanged: () => void;
  embedded?: boolean;
}) {
  const { toast } = useToast();
  const [view, setView] = useState<View>({ mode: 'list' });
  const [draft, setDraft] = useState('');
  const [dirty, setDirty] = useState(false);
  const [pendingView, setPendingView] = useState<View | null>(null);
  const [tab, setTab] = useState<'write' | 'preview'>('write');
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const activeName = view.mode === 'list' ? null : view.name;
  const activeDoc = activeName ? workspace.sources.find((s) => s.name === activeName) ?? null : null;

  useEffect(() => {
    if (view.mode !== 'list' && !activeDoc) setView({ mode: 'list' });
  }, [activeDoc, view.mode]);

  function open(next: View) {
    if (dirty && view.mode === 'edit') {
      setPendingView(next);
      return;
    }
    if (next.mode === 'list') {
      setView(next);
      return;
    }
    const doc = workspace.sources.find((s) => s.name === next.name);
    if (!doc) return;
    setDraft(doc.content);
    setDirty(false);
    setSaveError(null);
    setTab('write');
    setView(next);
  }

  function discardAndGo() {
    if (!pendingView) return;
    const next = pendingView;
    setPendingView(null);
    setDirty(false);
    if (next.mode === 'list') {
      setView(next);
      return;
    }
    const doc = workspace.sources.find((s) => s.name === next.name);
    if (!doc) return;
    setDraft(doc.content);
    setSaveError(null);
    setTab(next.mode === 'edit' ? 'write' : tab);
    setView(next);
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) {
      setCreateError('Give the source a name.');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const doc = await api.sources.create(workspace.id, name);
      setNewName('');
      onChanged();
      setDraft(doc.content);
      setDirty(false);
      setView({ mode: 'edit', name: doc.name });
      setTab('write');
      toast('Source created.');
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'The source could not be created.');
    } finally {
      setCreating(false);
    }
  }

  async function save() {
    if (!activeDoc) return;
    setSaving(true);
    setSaveError(null);
    try {
      const doc = await api.sources.update(workspace.id, activeDoc.name, draft);
      setDraft(doc.content);
      setDirty(false);
      onChanged();
      toast('Source saved. A version was kept.');
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'The source could not be saved.');
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!activeDoc) return;
    setRemoving(true);
    try {
      await api.sources.remove(workspace.id, activeDoc.name);
      setDeleteOpen(false);
      setView({ mode: 'list' });
      setDirty(false);
      onChanged();
      toast('Source removed.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The source could not be removed.', 'fail');
    } finally {
      setRemoving(false);
    }
  }

  async function restore(versionId: string) {
    if (!activeDoc) return;
    setRestoring(versionId);
    try {
      const doc = await api.sources.restore(workspace.id, activeDoc.name, versionId);
      setDraft(doc.content);
      setDirty(false);
      setView({ mode: 'edit', name: doc.name });
      setTab('write');
      onChanged();
      toast('Version restored. The current text is kept as a version.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'That version could not be restored.', 'fail');
    } finally {
      setRestoring(null);
    }
  }

  function download(doc: SourceDoc) {
    const url = URL.createObjectURL(new Blob([doc.content], { type: 'text/markdown' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = doc.name.endsWith('.md') ? doc.name : `${doc.name}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Source downloaded.');
  }

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (file.size > 1024 * 1024) {
      toast('Keep uploads under 1 MB.', 'fail');
      return;
    }
    setUploading(true);
    try {
      const text = await file.text();
      const name = file.name.replace(/\.(md|markdown|txt)$/i, '') || 'Uploaded source';
      const doc = await api.sources.create(workspace.id, name, text);
      onChanged();
      setDraft(doc.content);
      setDirty(false);
      setView({ mode: 'edit', name: doc.name });
      setTab('write');
      toast('Source uploaded.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The file could not be read.', 'fail');
    } finally {
      setUploading(false);
    }
  }

  const header = (
    <div className="folio__head">
      <div>
        <p className="eyebrow">Sources</p>
        <h2 className="folio__title">
          Notes <span className="folio__count">{String(workspace.sources.length).padStart(2, '0')}</span>
        </h2>
      </div>
      <div className="folio__head-actions">
        <button
          type="button"
          className="icon-btn icon-btn--sm"
          aria-label="Upload a source"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
        >
          <Icon name="upload" size={16} />
        </button>
        <button
          type="button"
          className="icon-btn icon-btn--sm"
          aria-label="New source"
          onClick={() => {
            setView({ mode: 'list' });
            setNewName('');
            setCreateError(null);
            requestAnimationFrame(() => {
              document.getElementById(`source-name-${embedded ? 'drawer' : 'folio'}`)?.focus();
            });
          }}
        >
          <Icon name="plus" size={16} />
        </button>
      </div>
    </div>
  );

  const newForm = (
    <form className="folio__new" onSubmit={create}>
      <label className="sr-only" htmlFor={`source-name-${embedded ? 'drawer' : 'folio'}`}>
        New source name
      </label>
      <input
        id={`source-name-${embedded ? 'drawer' : 'folio'}`}
        className="input input--sm"
        value={newName}
        onChange={(e) => setNewName(e.target.value)}
        placeholder="New source name"
        autoComplete="off"
      />
      <Button type="submit" size="sm" variant="outline" loading={creating}>
        Create
      </Button>
      {createError && <FormError>{createError}</FormError>}
    </form>
  );

  return (
    <div className={`folio${embedded ? ' folio--embedded' : ''}`}>
      {!embedded && header}
      <input
        ref={fileRef}
        type="file"
        accept=".md,.markdown,.txt,text/plain,text/markdown"
        hidden
        onChange={upload}
      />

      {view.mode === 'list' && (
        <>
          {embedded && (
            <div className="folio__embedded-bar">
              <span>{workspace.sources.length} sources</span>
              <div>
                <Button
                  size="sm"
                  variant="quiet"
                  icon="upload"
                  loading={uploading}
                  onClick={() => fileRef.current?.click()}
                >
                  Upload
                </Button>
              </div>
            </div>
          )}
          {newForm}
          {workspace.sources.length === 0 ? (
            <div className="folio__body" data-lenis-prevent>
              <EmptyState title={emptyState.sources.title} body={emptyState.sources.body} />
            </div>
          ) : (
            <div className="folio__body folio__body--list" data-lenis-prevent>
              <ul className="source-list">
                {workspace.sources.map((s) => (
                  <li key={s.id}>
                    <button type="button" className="source-row" onClick={() => open({ mode: 'edit', name: s.name })}>
                      <span className="source-row__icon" aria-hidden="true">
                        <Icon name="file" size={17} />
                      </span>
                      <span className="source-row__body">
                        <span className="source-row__name">{s.name}</span>
                        <span className="source-row__meta">
                          {relativeTime(s.updatedAt)} · {s.versions.length} versions
                        </span>
                      </span>
                      <Icon name="arrow-right" size={15} className="source-row__arrow" />
                    </button>
                  </li>
                ))}
              </ul>
              <p className="folio__note">Every save keeps a version. The model can draft here and patch later.</p>
            </div>
          )}
        </>
      )}

      {view.mode === 'edit' && activeDoc && (
        <div className="source-editor">
          <div className="source-editor__bar">
            <button
              type="button"
              className="icon-btn icon-btn--sm"
              aria-label="Back to sources"
              onClick={() => open({ mode: 'list' })}
            >
              <Icon name="arrow-left" size={16} />
            </button>
            <div className="source-editor__id">
              <span className="source-editor__name">{activeDoc.name}</span>
              <span className={`source-editor__dirty${dirty ? ' is-dirty' : ''}`}>
                {dirty ? 'Unsaved' : 'Saved'}
              </span>
            </div>
            <div className="source-editor__actions">
              <Button size="sm" onClick={save} loading={saving} disabled={!dirty}>
                Save
              </Button>
              <Popover
                label="Source actions"
                trigger={<Icon name="more" size={17} />}
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
                        open({ mode: 'history', name: activeDoc.name });
                      }}
                    >
                      <Icon name="history" size={16} />
                      History
                    </button>
                    <button
                      type="button"
                      className="menu-item"
                      onClick={() => {
                        close();
                        download(activeDoc);
                      }}
                    >
                      <Icon name="download" size={16} />
                      Download .md
                    </button>
                    <button
                      type="button"
                      className="menu-item menu-item--danger"
                      onClick={() => {
                        close();
                        setDeleteOpen(true);
                      }}
                    >
                      <Icon name="trash" size={16} />
                      Delete source
                    </button>
                  </>
                )}
              </Popover>
            </div>
          </div>

          <div className="source-editor__tabs">
            <div className="seg" role="tablist" aria-label="Editor mode">
              <button
                type="button"
                role="tab"
                aria-selected={tab === 'write'}
                className={tab === 'write' ? 'is-current' : ''}
                onClick={() => setTab('write')}
              >
                Write
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={tab === 'preview'}
                className={tab === 'preview' ? 'is-current' : ''}
                onClick={() => setTab('preview')}
              >
                Preview
              </button>
            </div>
            <span className="source-editor__meta">{draft.trim() ? `${draft.trim().split(/\s+/).length} words` : 'Empty'}</span>
          </div>

          {pendingView && (
            <div className="source-editor__discard" role="alert">
              <span>Discard unsaved changes?</span>
              <div>
                <Button size="sm" variant="quiet" onClick={() => setPendingView(null)}>
                  Keep editing
                </Button>
                <Button size="sm" variant="danger" onClick={discardAndGo}>
                  Discard
                </Button>
              </div>
            </div>
          )}

          {saveError && <FormError>{saveError}</FormError>}

          <div className="source-editor__body" data-lenis-prevent>
            {tab === 'write' ? (
              <textarea
                className="source-editor__textarea"
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setDirty(true);
                }}
                spellCheck
                aria-label={`Edit ${activeDoc.name}`}
              />
            ) : draft.trim() ? (
              <div className="source-editor__preview">
                <Markdown content={draft} videos={workspace.videos} />
              </div>
            ) : (
              <p className="source-editor__empty">Nothing written yet.</p>
            )}
          </div>
          <footer className="source-editor__foot">
            <span>Edited {relativeTime(activeDoc.updatedAt)}</span>
            <span>{activeDoc.versions.length} versions</span>
          </footer>
        </div>
      )}

      {view.mode === 'history' && activeDoc && (
        <div className="source-history">
          <div className="source-editor__bar">
            <button
              type="button"
              className="icon-btn icon-btn--sm"
              aria-label="Back to editor"
              onClick={() => open({ mode: 'edit', name: activeDoc.name })}
            >
              <Icon name="arrow-left" size={16} />
            </button>
            <div className="source-editor__id">
              <span className="source-editor__name">History</span>
              <span className="source-editor__dirty">{activeDoc.versions.length} versions</span>
            </div>
          </div>
          <div className="source-history__body" data-lenis-prevent>
            <p className="source-history__doc">{activeDoc.name}</p>
            <ol className="version-list">
              {[...activeDoc.versions].reverse().map((v, i) => (
                <li key={v.id} className={`version${i === 0 ? ' is-current' : ''}`}>
                  <div className="version__top">
                    <span className="version__time">{stamp(v.ts)}</span>
                    {i === 0 && <span className="version__now">current</span>}
                  </div>
                  <p className="version__note">{v.note}</p>
                  <p className="version__preview">
                    {v.content.replace(/[#*_`>]/g, '').replace(/\s+/g, ' ').trim().slice(0, 110) || 'Empty'}
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    loading={restoring === v.id}
                    disabled={i === 0}
                    onClick={() => restore(v.id)}
                  >
                    Restore
                  </Button>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      <Dialog
        open={deleteOpen}
        title="Delete this source?"
        description={`“${activeDoc?.name ?? ''}” and its versions are removed. Citations that point to it stay in old answers.`}
        onClose={() => setDeleteOpen(false)}
        footer={
          <>
            <Button variant="quiet" onClick={() => setDeleteOpen(false)}>
              Keep it
            </Button>
            <Button variant="danger" loading={removing} onClick={remove}>
              Delete source
            </Button>
          </>
        }
      />
    </div>
  );
}
