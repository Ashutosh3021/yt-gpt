import { Link } from 'react-router-dom';
import { Wordmark } from '../../components/Wordmark';
import { SignalMeter } from '../../components/SignalMeter';
import { Icon } from '../../components/Icon';
import { Popover } from '../../components/Popover';
import { GroundingChip, Badge } from '../../components/Chip';
import { UserMenu } from '../../components/GlobalTopbar';
import type { Grounding, Workspace } from '../../types';

export function WorkspaceTopbar({
  workspace,
  workspaces,
  grounding,
  modelLabel,
  onOpenLibrary,
  onOpenSources,
  onOpenSettings,
}: {
  workspace: Workspace;
  workspaces: Workspace[];
  grounding: Grounding;
  modelLabel: string;
  onOpenLibrary: () => void;
  onOpenSources: () => void;
  onOpenSettings: () => void;
}) {
  return (
    <header className="wtop">
      <div className="wtop__left">
        <Link to="/app" className="wtop__back" aria-label="All workspaces">
          <Icon name="arrow-left" size={18} />
        </Link>
        <span className="wtop__brand">
          <Wordmark />
        </span>
        <span className="wtop__rule" aria-hidden="true" />
        <Popover
          label="Switch workspace"
          trigger={
            <span className="ws-switch">
              <span className="ws-switch__name">{workspace.name}</span>
              <Icon name="chevron-down" size={15} />
            </span>
          }
          triggerClassName="popover__trigger--workspace"
          panelClassName="menu-panel menu-panel--switch"
          align="left"
        >
          {(close) => (
            <>
              <div className="menu-head">
                <span className="eyebrow">Workspaces</span>
                <span className="menu-head__count">{workspaces.length}</span>
              </div>
              <div className="menu-list">
                {workspaces.map((w) => (
                  <Link
                    key={w.id}
                    to={`/w/${w.id}`}
                    className={`menu-item menu-item--workspace${w.id === workspace.id ? ' is-current' : ''}`}
                    aria-current={w.id === workspace.id ? 'page' : undefined}
                    onClick={close}
                  >
                    <span className="menu-item__main">
                      <span className="menu-item__name">{w.name}</span>
                      <span className="menu-item__meta">
                        {w.videos.length} videos · {w.sessions.length} sessions
                      </span>
                    </span>
                    {w.demo && <Badge tone="neutral">sample</Badge>}
                    {w.id === workspace.id && <span className="menu-item__mark" aria-hidden="true" />}
                  </Link>
                ))}
              </div>
              <div className="menu-rule" />
              <Link to="/app" className="menu-item" onClick={close}>
                <Icon name="library" size={16} />
                All workspaces
              </Link>
            </>
          )}
        </Popover>
      </div>

      <div className="wtop__center">
        <span className="wtop__local">
          <SignalMeter bars={10} />
          <span>local</span>
        </span>
        <span className="wtop__dot" aria-hidden="true" />
        <GroundingChip grounding={grounding} />
        <span className="wtop__dot" aria-hidden="true" />
        <span className="wtop__model" title="Model for this session">
          {modelLabel}
        </span>
      </div>

      <div className="wtop__right">
        <button type="button" className="wtop__mobile-btn" onClick={onOpenLibrary} aria-label="Open library">
          <Icon name="library" size={18} />
        </button>
        <button type="button" className="wtop__mobile-btn" onClick={onOpenSources} aria-label="Open sources">
          <Icon name="file" size={18} />
        </button>
        <Link to={`/w/${workspace.id}/transcript`} className="wtop__transcript">
          <Icon name="code" size={16} />
          Transcript
        </Link>
        <button type="button" className="icon-btn" onClick={onOpenSettings} aria-label="Session settings">
          <Icon name="settings" size={18} />
        </button>
        <UserMenu />
      </div>
    </header>
  );
}
