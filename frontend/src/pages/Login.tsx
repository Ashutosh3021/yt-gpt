import { useRef, useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { isDemo } from '../api';
import { DEMO_EMAIL, DEMO_PASSWORD } from '../data/demo';
import { transitionNavigate } from '../motion/navigate';
import { PageMeta } from '../components/PageMeta';
import { Wordmark } from '../components/Wordmark';
import { SignalMeter } from '../components/SignalMeter';
import { Button } from '../components/Button';
import { Field, FormError } from '../components/Field';
import { Icon } from '../components/Icon';

function ProofStrip() {
  return (
    <div className="proof" data-reveal="up" data-intro data-delay="0.24" aria-label="Example answer with timecoded sources">
      <div className="proof__head">
        <span className="proof__label">Sample answer</span>
        <span className="proof__state">strictly grounded</span>
      </div>
      <p className="proof__q">What does attention actually do?</p>
      <div className="proof__body">
        <div className="proof__route" aria-hidden="true">
          <span className="proof__line" />
          <span className="proof__node" />
          <span className="proof__node proof__node--2" />
        </div>
        <p className="proof__a">
          Each token routes information from earlier positions, then mixes the result.
          <span className="proof__cite">02:14</span>
          <span className="proof__cite">08:41</span>
        </p>
      </div>
    </div>
  );
}

export function LoginPage() {
  const { user, signIn, signUp, demo } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<'form' | 'demo' | null>(null);
  const submitting = useRef(false);

  const from = (location.state as { from?: string } | null)?.from || '/app';

  if (user && !submitting.current) {
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === 'signup' && !name.trim()) {
      setError('Add a display name.');
      return;
    }
    if (!email.trim()) {
      setError('Add an email address.');
      return;
    }
    if (!password) {
      setError('Add a password.');
      return;
    }
    submitting.current = true;
    setBusy('form');
    try {
      if (mode === 'signin') await signIn(email, password);
      else await signUp(name, email, password);
      await transitionNavigate(navigate, from);
    } catch (err) {
      submitting.current = false;
      setBusy(null);
      setError(err instanceof Error ? err.message : 'That did not work. Try again.');
    }
  }

  async function handleDemo() {
    setError(null);
    submitting.current = true;
    setBusy('demo');
    try {
      await demo();
      await transitionNavigate(navigate, '/app');
    } catch (err) {
      submitting.current = false;
      setBusy(null);
      setError(err instanceof Error ? err.message : 'The sample workspace could not be opened.');
    }
  }

  return (
    <>
      <PageMeta
        title="Sign in"
        description="Open a local yt-gpt workspace. Turn YouTube links into clean transcripts and ask questions with timecoded citations."
        path="/login"
      />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <main id="main" className="login">
        <section className="login__hero">
          <div className="login__hero-top">
            <Wordmark light />
            <span className="login__status">
              <SignalMeter bars={9} />
              <span>local · 127.0.0.1</span>
            </span>
          </div>

          <div className="login__hero-body">
            <p className="eyebrow eyebrow--light" data-reveal="fade" data-intro>
              Local research desk
            </p>
            <h1 className="login__title" data-split="lines" data-intro>
              Ask the video.
              <br />
              Get the minute.
            </h1>
            <p className="login__lede" data-reveal="up" data-intro data-delay="0.16">
              Turn YouTube links into clean transcripts, then ask questions that point back to the exact
              second. Captions first. Citations always.
            </p>
            <ProofStrip />
          </div>

          <footer className="login__hero-foot" data-reveal="fade" data-intro data-delay="0.34">
            <span>Captions first</span>
            <span>No telemetry</span>
            <span>Your model, your key</span>
          </footer>
        </section>

        <section className="login__panel">
          <div className="login__form-wrap">
            <p className="eyebrow">Local access</p>
            <div className="login__switch" role="tablist" aria-label="Access mode">
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'signin'}
                className={mode === 'signin' ? 'is-current' : ''}
                onClick={() => {
                  setMode('signin');
                  setError(null);
                }}
              >
                Sign in
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'signup'}
                className={mode === 'signup' ? 'is-current' : ''}
                onClick={() => {
                  setMode('signup');
                  setError(null);
                }}
              >
                Create profile
              </button>
            </div>

            <h2 className="login__form-title">
              {mode === 'signin' ? 'Welcome back.' : 'A new profile.'}
            </h2>
            <p className="login__form-sub">
              {mode === 'signin'
                ? 'Your workspaces are on this machine. Sign in to open them.'
                : 'Profiles are local. One name, one email, one password.'}
            </p>

            <form className="login__form" onSubmit={handleSubmit} noValidate>
              {mode === 'signup' && (
                <Field label="Name" htmlFor="login-name">
                  <input
                    id="login-name"
                    className="input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    placeholder="Ada Lovelace"
                  />
                </Field>
              )}
              <Field label="Email" htmlFor="login-email">
                <input
                  id="login-email"
                  className="input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="you@local"
                  spellCheck={false}
                />
              </Field>
              <Field
                label="Password"
                htmlFor="login-password"
                hint={mode === 'signup' ? '6 characters or more' : undefined}
              >
                <input
                  id="login-password"
                  className="input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                  placeholder="••••••••"
                />
              </Field>

              {error && <FormError>{error}</FormError>}

              <Button type="submit" variant="primary" block loading={busy === 'form'} iconRight="arrow-right">
                {mode === 'signin' ? 'Enter workspace' : 'Create profile'}
              </Button>
            </form>

            {isDemo && (
              <div className="login__demo">
                <div className="login__demo-rule">
                  <span>or</span>
                </div>
                <Button
                  variant="outline"
                  block
                  icon="spark"
                  loading={busy === 'demo'}
                  onClick={handleDemo}
                >
                  Open the sample workspace
                </Button>
                <p className="login__demo-note">
                  Sample profile: {DEMO_EMAIL} / {DEMO_PASSWORD}. Demo data stays in this browser.
                </p>
              </div>
            )}

            <p className="login__fine">
              <Icon name="lock" size={14} />
              The server runs on this machine. No account leaves it.
            </p>
          </div>
        </section>
      </main>
    </>
  );
}
