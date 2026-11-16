import { Link } from 'react-router-dom';

export function Wordmark({ light = false, asLink = true }: { light?: boolean; asLink?: boolean }) {
  const body = (
    <>
      <span className="wordmark__mark" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="16" height="16" fill="none">
          <rect x="1.2" y="1.2" width="13.6" height="13.6" stroke="currentColor" strokeWidth="1.4" />
          <rect x="9.2" y="9.2" width="3.2" height="3.2" fill="currentColor" />
          <path d="M4.4 9.2h3.2M4.4 4.4v7.6" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      </span>
      <span className="wordmark__text">yt-gpt</span>
    </>
  );
  return asLink ? (
    <Link to="/app" className={`wordmark${light ? ' wordmark--light' : ''}`} aria-label="yt-gpt, workspaces">
      {body}
    </Link>
  ) : (
    <span className={`wordmark${light ? ' wordmark--light' : ''}`}>{body}</span>
  );
}
