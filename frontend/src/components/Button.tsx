import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Icon, type IconName } from './Icon';

type Variant = 'primary' | 'outline' | 'quiet' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: IconName;
  iconRight?: IconName;
  loading?: boolean;
  block?: boolean;
  children?: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  loading = false,
  block = false,
  className = '',
  disabled,
  children,
  ...rest
}: Props) {
  return (
    <button
      type="button"
      className={`btn btn--${variant} btn--${size}${block ? ' btn--block' : ''}${loading ? ' is-loading' : ''} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      <span className="btn__fill" aria-hidden="true" />
      {icon && <Icon name={icon} size={size === 'sm' ? 15 : 17} className="btn__icon" />}
      {children && <span className="btn__label">{children}</span>}
      {iconRight && <Icon name={iconRight} size={size === 'sm' ? 15 : 17} className="btn__icon btn__icon--right" />}
    </button>
  );
}
