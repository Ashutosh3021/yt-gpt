import type { ReactNode } from 'react';

export function LoadingPane({ label = 'Opening' }: { label?: string }) {
  return (
    <div className="loading-pane" role="status" aria-live="polite">
      <span className="loading-pane__bar" aria-hidden="true" />
      <span className="loading-pane__label">{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
  className = '',
}: {
  title: string;
  body: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`empty-state ${className}`}>
      <span className="empty-state__rule" aria-hidden="true" />
      <h2 className="empty-state__title">{title}</h2>
      <p className="empty-state__body">{body}</p>
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
