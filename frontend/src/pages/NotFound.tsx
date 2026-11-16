import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { PageMeta } from '../components/PageMeta';
import { Wordmark } from '../components/Wordmark';
import { Icon } from '../components/Icon';

export function NotFoundPage() {
  const { user } = useAuth();
  const home = user ? '/app' : '/login';

  return (
    <>
      <PageMeta
        title="Page not found"
        description="There is no page at this address. Return to the workspaces or sign in to the local server."
        path="/404"
      />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="nf__top">
        <Wordmark />
        <Link to={home} className="nf__back">
          <Icon name="arrow-left" size={16} />
          {user ? 'All workspaces' : 'Sign in'}
        </Link>
      </header>
      <main id="main" className="nf" tabIndex={-1}>
        <div className="nf__scope" aria-hidden="true">
          <svg viewBox="0 0 900 220" preserveAspectRatio="none" fill="none">
            <line className="nf__baseline" x1="0" y1="110" x2="900" y2="110" />
            <path
              className="nf__wave"
              d="M0 110H270c8 0 10-2 12-10l10-32c3-10 8-12 14 0l12 34 8 18c3 7 7 8 12 0l9-20c4-8 8-8 12 0l9 20c4 8 9 8 14 0l8-16c4-8 9-8 13 0l7 14c4 8 9 8 14 0l6-10c5-8 10-8 15 0l8 12c5 7 10 7 15 0l7-8c6-6 11-6 16 0l8 6c6 4 12 4 18 0l8-6c6-4 12-4 18 0l7 4c6 3 12 3 18 0l8-4c6-3 12-3 18 0l7 2c6 2 12 2 18 0l8-2c6-1 12-1 18 0l7 1c6 1 12 1 18 0h130"
              pathLength={1}
            />
            <circle className="nf__node" cx="490" cy="110" r="3" />
          </svg>
        </div>

        <div className="nf__body">
          <p className="eyebrow" data-reveal="fade" data-intro>
            404 · no signal
          </p>
          <h1 className="nf__title" data-split="lines" data-intro>
            No signal at this address.
          </h1>
          <p className="nf__lede" data-reveal="up" data-intro data-delay="0.12">
            The page may have moved, or the workspace was deleted. The local files are still under
            <code> ~/.yt-gpt</code>.
          </p>
          <div className="nf__actions" data-reveal="up" data-intro data-delay="0.2">
            <Link to={home} className="btn btn--primary btn--md">
              <span className="btn__fill" aria-hidden="true" />
              <span className="btn__label">{user ? 'Back to workspaces' : 'Sign in'}</span>
              <Icon name="arrow-right" size={17} className="btn__icon btn__icon--right" />
            </Link>
            <Link to={user ? '/settings' : '/'} className="btn btn--quiet btn--md">
              <span className="btn__label">{user ? 'Settings' : 'Home'}</span>
            </Link>
          </div>
        </div>

        <footer className="nf__foot">
          <span>yt-gpt</span>
          <span>127.0.0.1</span>
        </footer>
      </main>
    </>
  );
}
