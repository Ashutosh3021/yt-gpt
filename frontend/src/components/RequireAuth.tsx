import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Wordmark } from './Wordmark';
import { SignalMeter } from './SignalMeter';

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="auth-check" role="status" aria-live="polite">
        <Wordmark asLink={false} />
        <span className="auth-check__line" aria-hidden="true" />
        <p className="auth-check__label">
          <SignalMeter bars={8} /> Checking local session
        </p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }

  return <>{children}</>;
}
