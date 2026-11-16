export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 'recently';
  const diff = Math.max(0, Date.now() - then) / 1000;
  if (diff < 45) return 'just now';
  if (diff < 3600) {
    const m = Math.max(1, Math.round(diff / 60));
    return `${m} min ago`;
  }
  if (diff < 86400) {
    const h = Math.round(diff / 3600);
    return `${h} h ago`;
  }
  if (diff < 86400 * 7) {
    const d = Math.round(diff / 86400);
    return `${d} d ago`;
  }
  return new Intl.DateTimeFormat('en', { day: 'numeric', month: 'short' }).format(new Date(then));
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
