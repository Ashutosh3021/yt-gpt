import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { prefersReducedMotion } from '../engine/env';

export function SignalMeter({ bars = 14, className = '' }: { bars?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const els = [...root.querySelectorAll<HTMLElement>('.signal-meter__bar')];
    if (!els.length) return;
    if (prefersReducedMotion()) {
      els.forEach((el, i) => {
        el.style.transform = `scaleY(${0.25 + ((i * 7) % 11) / 14})`;
      });
      return;
    }
    const tick = () => {
      const t = performance.now() / 1000;
      els.forEach((el, i) => {
        const v = 0.18 + Math.abs(Math.sin(t * (1.15 + i * 0.07) + i * 0.55)) * 0.82;
        el.style.transform = `scaleY(${v.toFixed(3)})`;
      });
    };
    tick();
    gsap.ticker.add(tick);
    return () => gsap.ticker.remove(tick);
  }, []);

  return (
    <span ref={ref} className={`signal-meter ${className}`} aria-hidden="true">
      {Array.from({ length: bars }, (_, i) => (
        <span key={i} className="signal-meter__bar" />
      ))}
    </span>
  );
}
