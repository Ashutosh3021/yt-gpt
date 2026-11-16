import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useToast } from './Toast';
import { Wordmark } from './Wordmark';
import { SignalMeter } from './SignalMeter';
import { Icon } from './Icon';
import { Popover } from './Popover';

export function GlobalTopbar({ page, crumb }: { page: string; crumb?: ReactNode }) {
  return (
    <header className="topbar">
      <div className="topbar__left">
        <Wordmark />
        <span className="topbar__rule" aria-hidden="true" />
        <span className="topbar__page">{crumb ?? page}</span>
      </div>
      <div className="topbar__right">
        <span className="topbar__local">
          <SignalMeter bars={10} />
          <span>local</span>
        </span>
        <Link to="/settings" className="icon-btn" aria-label="Settings">
          <Icon name="settings" size={18} />
        </Link>
        <UserMenu />
      </div>
    </header>
  );
}

export function UserMenu() {
  const { user, signOut } = useAuth();
  const { toast } = useToast();
  const initials = (user?.name || user?.email || '?')
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join('');

  return (
    <Popover
      label="Account menu"
      trigger={<span className="avatar">{initials || '?'}</span>}
      triggerClassName="popover__trigger--avatar"
      panelClassName="menu-panel menu-panel--account"
    >
      {(close) => (
        <>
          <div className="menu-account">
            <p className="menu-account__name">{user?.name}</p>
            <p className="menu-account__email">{user?.email}</p>
          </div>
          <div className="menu-rule" />
          <Link to="/settings" className="menu-item" onClick={close}>
            <Icon name="settings" size={16} />
            Settings
          </Link>
          <button
            type="button"
            className="menu-item"
            onClick={async () => {
              close();
              await signOut();
              toast('Signed out. The local data stays on disk.');
            }}
          >
            <Icon name="logout" size={16} />
            Sign out
          </button>
        </>
      )}
    </Popover>
  );
}
