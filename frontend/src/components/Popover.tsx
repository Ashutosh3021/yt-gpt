import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

export function Popover({
  trigger,
  children,
  label,
  align = 'right',
  triggerClassName = '',
  panelClassName = '',
}: {
  trigger: ReactNode;
  children: (close: () => void) => ReactNode;
  label: string;
  align?: 'left' | 'right';
  triggerClassName?: string;
  panelClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener('pointerdown', onPointer);
    document.addEventListener('keydown', onKey);
    const t = window.setTimeout(() => {
      panelRef.current?.querySelector<HTMLElement>('[data-autofocus], button, a, input, textarea, select')?.focus();
    }, 20);
    return () => {
      document.removeEventListener('pointerdown', onPointer);
      document.removeEventListener('keydown', onKey);
      window.clearTimeout(t);
    };
  }, [open]);

  return (
    <div className="popover" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className={`popover__trigger ${triggerClassName}`}
        aria-expanded={open}
        aria-controls={id}
        aria-label={label}
        onClick={() => setOpen((v) => !v)}
      >
        {trigger}
      </button>
      {open && (
        <div
          ref={panelRef}
          id={id}
          className={`popover__panel popover__panel--${align} ${panelClassName}`}
          aria-label={label}
          data-lenis-prevent
        >
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}
