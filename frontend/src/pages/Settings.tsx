import { useEffect, useState, type FormEvent } from 'react';
import { api, isDemo } from '../api';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../auth/AuthContext';
import { useToast } from '../components/Toast';
import { PageMeta } from '../components/PageMeta';
import { GlobalTopbar } from '../components/GlobalTopbar';
import { Button } from '../components/Button';
import { Field, FormError } from '../components/Field';
import { Icon } from '../components/Icon';
import { LoadingPane } from '../components/States';
import { providerModels, site } from '../data/site';
import type { LlmSettings } from '../types';

const defaults: Record<LlmSettings['provider'], string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com',
  google: 'https://generativelanguage.googleapis.com/v1beta',
  openrouter: 'https://openrouter.ai/api/v1',
  ollama: 'http://127.0.0.1:11434/v1',
  custom: '',
};

const providers: { id: LlmSettings['provider']; label: string }[] = [
  { id: 'openai', label: 'OpenAI' },
  { id: 'anthropic', label: 'Anthropic' },
  { id: 'google', label: 'Google' },
  { id: 'openrouter', label: 'OpenRouter' },
  { id: 'ollama', label: 'Ollama (local)' },
  { id: 'custom', label: 'Custom endpoint' },
];

export function SettingsPage() {
  const { user, signOut } = useAuth();
  const { toast } = useToast();
  const { data, loading, error, reload, setData } = useAsync(() => api.settings.get(), []);
  const [provider, setProvider] = useState<LlmSettings['provider']>('openai');
  const [baseUrl, setBaseUrl] = useState(defaults.openai);
  const [model, setModel] = useState('gpt-4.1-mini');
  const [embeddingModel, setEmbeddingModel] = useState('text-embedding-3-small');
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildResult, setRebuildResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    if (!data) return;
    setProvider(data.llm.provider);
    setBaseUrl(data.llm.baseUrl);
    setModel(data.llm.model);
    setEmbeddingModel(data.llm.embeddingModel);
    setApiKey('');
  }, [data]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      const saved = await api.settings.saveLlm({
        provider,
        baseUrl: baseUrl.trim(),
        model: model.trim(),
        embeddingModel: embeddingModel.trim(),
        ...(apiKey.trim() ? { apiKey: apiKey.trim() } : {}),
      });
      setData(saved);
      setApiKey('');
      toast('Model settings saved.');
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'The settings did not save.');
    } finally {
      setSaving(false);
    }
  }

  async function test() {
    setTesting(true);
    setTestResult(null);
    try {
      setTestResult(await api.settings.testLlm());
    } catch (err) {
      setTestResult({ ok: false, message: err instanceof Error ? err.message : 'The test did not run.' });
    } finally {
      setTesting(false);
    }
  }

  async function rebuild() {
    setRebuilding(true);
    setRebuildResult(null);
    try {
      setRebuildResult(await api.settings.rebuild());
    } catch (err) {
      setRebuildResult({ ok: false, message: err instanceof Error ? err.message : 'The rebuild did not run.' });
    } finally {
      setRebuilding(false);
    }
  }

  async function signOutNow() {
    await signOut();
    toast('Signed out. The local data stays on disk.');
  }

  const models = providerModels[provider] ?? [];
  const modelList = model && !models.includes(model) ? [model, ...models] : models;

  return (
    <>
      <PageMeta
        title="Settings"
        description="Choose the model provider, inspect the local files and check the health of the yt-gpt workspace."
        path="/settings"
      />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <GlobalTopbar page="Settings" />
      <main id="main" className="settings" tabIndex={-1}>
        <header className="settings__head">
          <p className="eyebrow" data-reveal="fade" data-intro>
            Local configuration
          </p>
          <h1 className="settings__title" data-split="lines" data-intro>
            Settings
          </h1>
          <p className="settings__lede" data-reveal="up" data-intro data-delay="0.12">
            The model, the key and the local files. Nothing leaves this machine unless you point it at a
            provider.
          </p>
        </header>

        <div className="settings__grid">
          <nav className="settings__nav" aria-label="Settings sections">
            <a href="#model">Model</a>
            <a href="#local">Local data</a>
            <a href="#account">Account</a>
          </nav>

          <div className="settings__panels">
            {loading && !data && <LoadingPane label="Reading local settings" />}
            {error && !data && (
              <div className="settings-card" role="alert">
                <p>{error}</p>
                <Button variant="outline" size="sm" icon="retry" onClick={reload}>
                  Try again
                </Button>
              </div>
            )}

            {data && (
              <>
                <section className="settings-card" id="model" aria-labelledby="model-title">
                  <header className="settings-card__head">
                    <div>
                      <p className="eyebrow">Model</p>
                      <h2 id="model-title" className="settings-card__title">
                        The connection
                      </h2>
                      <p className="settings-card__body">
                        Bring a key or run a local model. The provider and model ids are examples, not
                        endorsements.
                      </p>
                    </div>
                    <span className={`status-pill${data.llm.hasKey ? ' is-ok' : ' is-idle'}`}>
                      <span className="status-pill__dot" aria-hidden="true" />
                      {data.llm.hasKey ? `Key ${data.llm.keyMasked}` : 'No key saved'}
                    </span>
                  </header>

                  <form className="settings-form" onSubmit={save}>
                    <div className="settings-form__row">
                      <Field label="Provider" htmlFor="settings-provider">
                        <select
                          id="settings-provider"
                          className="select"
                          value={provider}
                          onChange={(e) => {
                            const next = e.target.value as LlmSettings['provider'];
                            setProvider(next);
                            setModel(providerModels[next]?.[0] ?? '');
                            if (!baseUrl || baseUrl === defaults[provider]) setBaseUrl(defaults[next]);
                          }}
                        >
                          {providers.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.label}
                            </option>
                          ))}
                        </select>
                      </Field>
                      <Field label="Model" htmlFor="settings-model" hint="Type any id the provider accepts">
                        <input
                          id="settings-model"
                          className="input"
                          list="model-options"
                          value={model}
                          onChange={(e) => setModel(e.target.value)}
                          spellCheck={false}
                        />
                        <datalist id="model-options">
                          {modelList.map((m) => (
                            <option key={m} value={m} />
                          ))}
                        </datalist>
                      </Field>
                    </div>

                    <Field label="Base URL" htmlFor="settings-base" hint="The API root, not a chat path">
                      <input
                        id="settings-base"
                        className="input"
                        value={baseUrl}
                        onChange={(e) => setBaseUrl(e.target.value)}
                        spellCheck={false}
                        placeholder="https://api.openai.com/v1"
                      />
                    </Field>

                    <Field
                      label="Embedding model"
                      htmlFor="settings-embedding"
                      hint="Reserved for the planned embedding index; BM25 is used today"
                    >
                      <input
                        id="settings-embedding"
                        className="input"
                        value={embeddingModel}
                        onChange={(e) => setEmbeddingModel(e.target.value)}
                        spellCheck={false}
                        placeholder="text-embedding-3-small"
                      />
                    </Field>

                    <Field
                      label="API key"
                      htmlFor="settings-key"
                      hint={data.llm.hasKey ? 'Leave blank to keep the saved key' : 'Stored in the OS keyring'}
                    >
                      <input
                        id="settings-key"
                        className="input"
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={data.llm.hasKey ? '••••••••••••' : 'sk-...'}
                        autoComplete="off"
                        spellCheck={false}
                      />
                    </Field>

                    <div className="settings-capabilities" aria-label="Model capabilities">
                      <div>
                        <span className="settings-capabilities__label">Context</span>
                        <span className="settings-capabilities__value">{data.llm.capabilities.contextK}k</span>
                      </div>
                      <div>
                        <span className="settings-capabilities__label">Vision</span>
                        <span className={`settings-capabilities__value${data.llm.capabilities.vision ? ' is-on' : ''}`}>
                          {data.llm.capabilities.vision ? 'Yes' : 'No'}
                        </span>
                      </div>
                      <div>
                        <span className="settings-capabilities__label">Tools</span>
                        <span className={`settings-capabilities__value${data.llm.capabilities.tools ? ' is-on' : ''}`}>
                          {data.llm.capabilities.tools ? 'Yes' : 'No'}
                        </span>
                      </div>
                      <div>
                        <span className="settings-capabilities__label">Caching</span>
                        <span className={`settings-capabilities__value${data.llm.capabilities.caching ? ' is-on' : ''}`}>
                          {data.llm.capabilities.caching ? 'Yes' : 'No'}
                        </span>
                      </div>
                    </div>

                    {saveError && <FormError>{saveError}</FormError>}
                    {testResult && (
                      <p className={`test-result${testResult.ok ? ' is-ok' : ' is-fail'}`} role="status">
                        <span className="test-result__dot" aria-hidden="true" />
                        {testResult.message}
                      </p>
                    )}

                    <div className="settings-form__actions">
                      <Button type="submit" loading={saving}>
                        Save model
                      </Button>
                      <Button type="button" variant="outline" loading={testing} icon="wave" onClick={test}>
                        Test connection
                      </Button>
                    </div>
                    {isDemo && (
                      <p className="settings-note">
                        Demo mode. The key is not stored and the test is simulated. The real server writes keys
                        to the OS keyring.
                      </p>
                    )}
                  </form>
                </section>

                <section className="settings-card" id="local" aria-labelledby="local-title">
                  <header className="settings-card__head">
                    <div>
                      <p className="eyebrow">Local data</p>
                      <h2 id="local-title" className="settings-card__title">
                        What is on disk
                      </h2>
                      <p className="settings-card__body">
                        Videos, transcripts, notes and the search index live under the root. Moving the root
                        moves the workspace.
                      </p>
                    </div>
                  </header>

                  <dl className="settings-paths">
                    <div>
                      <dt>Root</dt>
                      <dd>
                        <code>{data.root}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>Workspaces</dt>
                      <dd>
                        <code>{site.storagePath}</code>
                      </dd>
                    </div>
                    <div>
                      <dt>Version</dt>
                      <dd>
                        <code>yt-gpt {data.version}</code>
                      </dd>
                    </div>
                  </dl>

                  <div className="doctor">
                    <div className="doctor__head">
                      <h3 className="doctor__title">Doctor</h3>
                      {isDemo && <span className="doctor__demo">sample checks</span>}
                    </div>
                    <ul>
                      {data.doctor.map((check) => (
                        <li key={check.label} className={`doctor__row${check.ok ? ' is-ok' : ' is-warn'}`}>
                          <span className="doctor__dot" aria-hidden="true" />
                          <span className="doctor__label">{check.label}</span>
                          <span className="doctor__value">{check.value}</span>
                          {check.hint && <span className="doctor__hint">{check.hint}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {rebuildResult && (
                    <p className={`test-result${rebuildResult.ok ? ' is-ok' : ' is-fail'}`} role="status">
                      <span className="test-result__dot" aria-hidden="true" />
                      {rebuildResult.message}
                    </p>
                  )}
                  <div className="settings-form__actions">
                    <Button
                      type="button"
                      variant="outline"
                      loading={rebuilding}
                      icon="database"
                      onClick={rebuild}
                    >
                      Rebuild derived files
                    </Button>
                    <span className="settings-note">Rebuild keeps the originals and rewrites chunks.</span>
                  </div>
                </section>

                <section className="settings-card" id="account" aria-labelledby="account-title">
                  <header className="settings-card__head">
                    <div>
                      <p className="eyebrow">Account</p>
                      <h2 id="account-title" className="settings-card__title">
                        This profile
                      </h2>
                      <p className="settings-card__body">
                        Profiles are local. The password stays in the local database.
                      </p>
                    </div>
                  </header>
                  <div className="account-row">
                    <span className="account-row__avatar" aria-hidden="true">
                      {(user?.name || '?').slice(0, 1).toUpperCase()}
                    </span>
                    <div className="account-row__body">
                      <p className="account-row__name">{user?.name}</p>
                      <p className="account-row__email">{user?.email}</p>
                    </div>
                    <Button variant="outline" size="sm" icon="logout" onClick={signOutNow}>
                      Sign out
                    </Button>
                  </div>
                  <p className="settings-note">
                    <Icon name="lock" size={14} />
                    The server listens on 127.0.0.1. Nothing is exposed to the network by default.
                  </p>
                </section>
              </>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
