import { useEffect } from 'react';
import { onPage, type PageFn } from '../engine';

export function usePage(fn: PageFn, deps: unknown[] = []) {
  useEffect(() => onPage(fn), deps);
}
