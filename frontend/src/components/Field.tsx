import type { ReactNode } from 'react';

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
  className = '',
}: {
  label: string;
  htmlFor: string;
  hint?: ReactNode;
  error?: string | null;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`field ${className}`}>
      <div className="field__top">
        <label className="field__label" htmlFor={htmlFor}>
          {label}
        </label>
        {hint && <span className="field__hint">{hint}</span>}
      </div>
      {children}
      {error && (
        <p className="field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function FormError({ children }: { children: ReactNode }) {
  return (
    <p className="form-error" role="alert">
      <span className="form-error__dot" aria-hidden="true" />
      {children}
    </p>
  );
}
