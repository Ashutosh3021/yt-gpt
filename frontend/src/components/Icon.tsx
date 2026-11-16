import type { SVGProps } from 'react';

export type IconName =
  | 'plus'
  | 'arrow-right'
  | 'arrow-left'
  | 'arrow-up-right'
  | 'x'
  | 'menu'
  | 'settings'
  | 'search'
  | 'file'
  | 'download'
  | 'upload'
  | 'trash'
  | 'chevron-down'
  | 'play'
  | 'clock'
  | 'check'
  | 'alert'
  | 'more'
  | 'copy'
  | 'retry'
  | 'logout'
  | 'key'
  | 'database'
  | 'user'
  | 'video'
  | 'message'
  | 'edit'
  | 'history'
  | 'eye'
  | 'code'
  | 'spark'
  | 'link'
  | 'library'
  | 'send'
  | 'stop'
  | 'lock'
  | 'external'
  | 'panel'
  | 'wave';

const paths: Record<IconName, React.ReactNode> = {
  plus: <path d="M12 5v14M5 12h14" />,
  'arrow-right': <path d="M4 12h15m-6-6 6 6-6 6" />,
  'arrow-left': <path d="M20 12H5m6-6-6 6 6 6" />,
  'arrow-up-right': <path d="M7 17 17 7M8 7h9v9" />,
  x: <path d="m6 6 12 12M18 6 6 18" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  settings: (
    <>
      <path d="M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.86 1.86-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V20h-2.63v-.08A1.7 1.7 0 0 0 11.3 18.4a1.7 1.7 0 0 0-1.88.34l-.06.06-1.86-1.86.06-.06A1.7 1.7 0 0 0 7.9 15a1.7 1.7 0 0 0-1.56-1.03H6.3v-2.63h.08A1.7 1.7 0 0 0 7.9 10.3a1.7 1.7 0 0 0-.34-1.88l-.06-.06 1.86-1.86.06.06A1.7 1.7 0 0 0 11.3 6.9a1.7 1.7 0 0 0 1.03-1.56V5.3h2.63v.08A1.7 1.7 0 0 0 16 6.9a1.7 1.7 0 0 0 1.88-.34l.06-.06 1.86 1.86-.06.06A1.7 1.7 0 0 0 19.4 10.3a1.7 1.7 0 0 0 1.56 1.03h.08v2.63h-.08A1.7 1.7 0 0 0 19.4 15Z" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </>
  ),
  file: (
    <>
      <path d="M6 3.8h7.5L18.5 9v11.2H6z" />
      <path d="M13.5 3.8V9h5" />
    </>
  ),
  download: <path d="M12 3v12m-5-5 5 5 5-5M5 20h14" />,
  upload: <path d="M12 16V4m-5 5 5-5 5 5M5 20h14" />,
  trash: <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" />,
  'chevron-down': <path d="m6 9 6 6 6-6" />,
  play: <path d="M8 5.5v13l10-6.5-10-6.5Z" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7v5.2l3.2 2" />
    </>
  ),
  check: <path d="m5 12.5 4.2 4.2L19 7" />,
  alert: <path d="M12 4 3.5 20h17L12 4Zm0 5v5m0 3v.2" />,
  more: (
    <>
      <circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
      <circle cx="19" cy="12" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  copy: (
    <>
      <rect x="8" y="8" width="12" height="12" rx="1" />
      <path d="M16 8V4H4v12h4" />
    </>
  ),
  retry: <path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5" />,
  logout: <path d="M14 4H5v16h9M10 12h11m-4-4 4 4-4 4" />,
  key: (
    <>
      <circle cx="8" cy="12" r="3.2" />
      <path d="M11.2 12H21m-4 0v4m-3-4v3" />
    </>
  ),
  database: (
    <>
      <ellipse cx="12" cy="5.5" rx="7.5" ry="2.6" />
      <path d="M4.5 5.5v13c0 1.4 3.4 2.6 7.5 2.6s7.5-1.2 7.5-2.6v-13M4.5 12c0 1.4 3.4 2.6 7.5 2.6s7.5-1.2 7.5-2.6" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.5 20c.6-3.8 3.4-5.8 7.5-5.8s6.9 2 7.5 5.8" />
    </>
  ),
  video: (
    <>
      <rect x="3" y="6" width="13" height="12" rx="1" />
      <path d="m16 10 5-3v10l-5-3" />
    </>
  ),
  message: <path d="M4 5h16v12H9l-5 4V5Z" />,
  edit: <path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Zm9.5-13 3.5 3.5" />,
  history: (
    <>
      <path d="M4 12a8 8 0 1 0 2.3-5.6M4 4v5h5" />
      <path d="M12 7v5.2l3.2 2" />
    </>
  ),
  eye: (
    <>
      <path d="M3 12s3.4-6 9-6 9 6 9 6-3.4 6-9 6-9-6-9-6Z" />
      <circle cx="12" cy="12" r="2.6" />
    </>
  ),
  code: <path d="m9 7-5 5 5 5m6-10 5 5-5 5" />,
  spark: <path d="M12 3v4m0 10v4M3 12h4m10 0h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />,
  link: <path d="M10 14a4.5 4.5 0 0 0 6.4 0l2.2-2.2a4.5 4.5 0 0 0-6.4-6.4L11 6.6M14 10a4.5 4.5 0 0 0-6.4 0l-2.2 2.2a4.5 4.5 0 0 0 6.4 6.4l1.2-1.2" />,
  library: (
    <>
      <path d="M4 4v16M8 4v16M12 4v16" />
      <path d="m16 5 4 14" />
    </>
  ),
  send: <path d="M4 12 20 4l-4 16-4.5-6.5L4 12Zm7.5 1.5L20 4" />,
  stop: <rect x="6" y="6" width="12" height="12" rx="1" fill="currentColor" stroke="none" />,
  lock: (
    <>
      <rect x="5" y="10" width="14" height="10" rx="1" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
  external: <path d="M14 4h6v6m0-6-9 9M19 14v5H5V5h5" />,
  panel: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="1" />
      <path d="M9 4v16" />
    </>
  ),
  wave: <path d="M3 12h3l2-6 4 12 3-8 2 2h4" />,
};

export function Icon({
  name,
  size = 18,
  className,
  strokeWidth = 1.6,
  ...rest
}: { name: IconName; size?: number; strokeWidth?: number } & Omit<SVGProps<SVGSVGElement>, 'name'>) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      {...rest}
    >
      {paths[name]}
    </svg>
  );
}
