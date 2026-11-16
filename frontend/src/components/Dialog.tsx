import { useEffect, useId, useRef, type ReactNode } from 'react';
import { Icon } from './Icon';

export function Dialog({
  open,
  title,
  description,
  children,
  footer,
  onClose,
}: {
  open: boolean;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      d.showModal();
      document.documentElement.classList.add('has-dialog');
    }
    if (!open && d.open) d.close();
    return () => {
      if (d.open) d.close();
      document.documentElement.classList.remove('has-dialog');
    };
  }, [open]);

  if (!open) return null;

  return (
    <dialog
      ref={ref}
      className="dialog"
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="dialog__panel" data-lenis-prevent>
        <header className="dialog__head">
          <h2 id={titleId} className="dialog__title">
            {title}
          </h2>
          <button type="button" className="icon-btn icon-btn--sm" aria-label="Close dialog" onClick={onClose}>
            <Icon name="x" size={17} />
          </button>
        </header>
        {description && (
          <p id={descId} className="dialog__body">
            {description}
          </p>
        )}
        {children && <div className="dialog__content">{children}</div>}
        {footer && <footer className="dialog__foot">{footer}</footer>}
      </div>
    </dialog>
  );
}
