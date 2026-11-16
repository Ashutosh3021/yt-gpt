import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../../api';
import { useAsync } from '../../hooks/useAsync';
import { useToast } from '../../components/Toast';
import { Drawer } from '../../components/Drawer';
import { Button } from '../../components/Button';
import { Field, FormError } from '../../components/Field';
import { Dialog } from '../../components/Dialog';
import { personas, providerModels } from '../../data/site';
import type { Grounding, PersonaId, Session, Workspace } from '../../types';

export function SessionSettings({
  open,
  onClose,
  workspace,
  session,
  onChanged,
}: {
  open: boolean;
  onClose: () => void;
  workspace: Workspace;
  session: Session | null;
  onChanged: () => void;
}) {
  const { toast } = useToast();
  const { data: app } = useAsync(() => (open ? api.settings.get() : Promise.resolve(null)), [open]);
  const [title, setTitle] = useState('');
  const [grounding, setGrounding] = useState<Grounding>('strict');
  const [personaId, setPersonaId] = useState<PersonaId>('default');
  const [personaPrompt, setPersonaPrompt] = useState('');
  const [modelOverride, setModelOverride] = useState('');
  const [useVisuals, setUseVisuals] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    if (!open || !session) return;
    setTitle(session.title);
    setGrounding(session.settings.grounding);
    setPersonaId(session.settings.personaId);
    setPersonaPrompt(session.settings.personaPrompt ?? '');
    setModelOverride(session.settings.modelOverride ?? '');
    setUseVisuals(session.settings.useVisuals);
    setError(null);
  }, [open, session?.id]);

  const persona = personas.find((p) => p.id === personaId) ?? personas[0];
  const vision = app?.llm.capabilities.vision ?? false;
  const workspaceVisuals = workspace.settings.useVisuals;
  const models = app ? providerModels[app.llm.provider] ?? [] : [];
  const modelOptions = modelOverride && !models.includes(modelOverride) ? [modelOverride, ...models] : models;

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!session) return;
    setSaving(true);
    setError(null);
    try {
      await api.sessions.update(workspace.id, session.id, {
        title: title.trim() || session.title,
        settings: {
          grounding,
          personaId,
          personaPrompt: personaId === 'custom' ? personaPrompt.trim() || null : null,
          modelOverride: modelOverride || null,
          useVisuals: useVisuals && vision && workspaceVisuals,
        },
      });
      onChanged();
      onClose();
      toast('Session settings saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The settings did not save.');
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!session) return;
    setRemoving(true);
    try {
      await api.sessions.remove(workspace.id, session.id);
      setDeleteOpen(false);
      onChanged();
      onClose();
      toast('Session deleted.');
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The session could not be deleted.', 'fail');
    } finally {
      setRemoving(false);
    }
  }

  return (
    <>
      <Drawer
        open={open}
        onClose={onClose}
        title="Session settings"
        eyebrow="This conversation"
      >
        {!session ? (
          <p className="drawer__empty">Choose a session first.</p>
        ) : (
          <form className="session-form" onSubmit={save}>
            <Field label="Session title" htmlFor="session-title">
              <input
                id="session-title"
                className="input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="What this session is about"
              />
            </Field>

            <fieldset className="radio-group">
              <legend className="field__label">Grounding</legend>
              <label className={`radio-card${grounding === 'strict' ? ' is-current' : ''}`}>
                <input
                  type="radio"
                  name="grounding"
                  value="strict"
                  checked={grounding === 'strict'}
                  onChange={() => setGrounding('strict')}
                />
                <span className="radio-card__body">
                  <span className="radio-card__title">Strictly grounded</span>
                  <span className="radio-card__text">
                    Answers use the videos first. If the sources do not cover it, the answer says so.
                  </span>
                </span>
              </label>
              <label className={`radio-card${grounding === 'interpretive' ? ' is-current' : ''}`}>
                <input
                  type="radio"
                  name="grounding"
                  value="interpretive"
                  checked={grounding === 'interpretive'}
                  onChange={() => setGrounding('interpretive')}
                />
                <span className="radio-card__body">
                  <span className="radio-card__title">Interpretive</span>
                  <span className="radio-card__text">
                    The model may reason beyond the videos. Inferences are marked as inferences.
                  </span>
                </span>
              </label>
            </fieldset>

            <Field label="Persona" htmlFor="session-persona" hint={persona.name}>
              <select
                id="session-persona"
                className="select"
                value={personaId}
                onChange={(e) => setPersonaId(e.target.value as PersonaId)}
              >
                {personas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <p className="field__note">{persona.description}</p>

            {personaId === 'custom' && (
              <Field
                label="Custom prompt"
                htmlFor="session-prompt"
                hint="Layered under the grounding rules"
              >
                <textarea
                  id="session-prompt"
                  className="textarea"
                  rows={4}
                  value={personaPrompt}
                  onChange={(e) => setPersonaPrompt(e.target.value)}
                  placeholder="Write the voice and the constraints you want."
                />
              </Field>
            )}

            <Field
              label="Model"
              htmlFor="session-model"
              hint={app ? `${app.llm.provider} · ${app.llm.model}` : 'Loading provider'}
            >
              <select
                id="session-model"
                className="select"
                value={modelOverride}
                onChange={(e) => setModelOverride(e.target.value)}
              >
                <option value="">Default ({app?.llm.model ?? 'provider model'})</option>
                {modelOptions.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </Field>

            <label className={`toggle-row${!vision || !workspaceVisuals ? ' is-disabled' : ''}`}>
              <input
                type="checkbox"
                checked={useVisuals}
                onChange={(e) => setUseVisuals(e.target.checked)}
                disabled={!vision || !workspaceVisuals}
              />
              <span className="toggle-row__track" aria-hidden="true">
                <span />
              </span>
              <span className="toggle-row__body">
                <span className="toggle-row__title">Use on-screen frames</span>
                <span className="toggle-row__text">
                  {!vision
                    ? 'This model does not report vision support.'
                    : !workspaceVisuals
                      ? 'Visuals are off for this workspace.'
                      : 'Adds frames to the context when a question is visual.'}
                </span>
              </span>
            </label>

            {error && <FormError>{error}</FormError>}

            <div className="session-form__actions">
              <Button type="submit" loading={saving}>
                Save settings
              </Button>
              <Button type="button" variant="quiet" onClick={onClose}>
                Cancel
              </Button>
            </div>

            <div className="session-danger">
              <p className="session-danger__title">Delete session</p>
              <p className="session-danger__text">
                The messages leave the workspace. The sources and videos stay.
              </p>
              <Button type="button" variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>
                Delete session
              </Button>
            </div>
          </form>
        )}
      </Drawer>

      <Dialog
        open={deleteOpen}
        title="Delete this session?"
        description={`“${session?.title ?? ''}” and its messages are removed. This cannot be undone from the app.`}
        onClose={() => setDeleteOpen(false)}
        footer={
          <>
            <Button variant="quiet" onClick={() => setDeleteOpen(false)}>
              Keep it
            </Button>
            <Button variant="danger" loading={removing} onClick={remove}>
              Delete session
            </Button>
          </>
        }
      />
    </>
  );
}
