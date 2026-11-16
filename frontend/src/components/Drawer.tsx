import { useEffect, useRef, type ReactNode, type RefObject } from 'react';
import { Icon } from './Icon';

export function useFocusTrap(active: boolean, ref: RefObject<HTMLElement | null>, onClose: () => void) {
  useEffect(() => {
    if (!active) return;
    const node = ref.current;
    if (!node) return;
    const previous = document.activeElement as HTMLElement | null;

    const focusables = () =>
      [...node.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )].filter((el) => el.offsetParent !== null || el === document.activeElement);

    const t = window.setTimeout(() => {
      const first = focusables()[0];
      (first ?? node).focus();
    }, 30);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;
      const list = focusables();
      if (!list.length) {
        e.preventDefault();
        return;
      }
      const first = list[0];
      const last = list[list.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKey);
    return () => {
      window.clearTimeout(t);
      document.removeEventListener('keydown', onKey);
      previous?.focus?.();
    };
  }, [active, ref, onClose]);
}

export function Drawer({
  open,
  onClose,
  title,
  eyebrow,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  eyebrow?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, panelRef, onClose);

  useEffect(() => {
    if (!open) return;
    document.documentElement.classList.add('has-drawer');
    return () => document.documentElement.classList.remove('has-drawer');
  }, [open]);

  return (
    <div className={`drawer${open ? ' is-open' : ''}`} aria-hidden={!open} inert={!open}>
      <button type="button" className="drawer__scrim" aria-label="Close panel" onClick={onClose} tabIndex={-1} />
      <div
        ref={panelRef}
        className="drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
      >
        <header className="drawer__head">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            <h2 className="drawer__title">{title}</h2>
          </div>
          <button type="button" className="icon-btn" aria-label={`Close ${title}`} onClick={onClose}>
            <Icon name="x" size={18} />
          </button>
        </header>
        <div className="drawer__body" data-lenis-prevent>{children}</div>
        {footer && <footer className="drawer__foot">{footer}</footer>}
      </div>
    </div>
  );
}
