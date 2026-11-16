import { gsap } from 'gsap';
import { prefersReducedMotion } from '../engine/env';

const NS = 'http://www.w3.org/2000/svg';
let started = false;
let active: HTMLElement | null = null;
let hideTimer = 0;

type Trace = {
  svg: SVGSVGElement;
  path: SVGPathElement;
  a: SVGCircleElement;
  b: SVGCircleElement;
};

function layer(): Trace | null {
  const svg = document.getElementById('signal-layer') as SVGSVGElement | null;
  if (!svg) return null;
  let path = svg.querySelector<SVGPathElement>('path.signal-path');
  let a = svg.querySelector<SVGCircleElement>('circle.signal-node--a');
  let b = svg.querySelector<SVGCircleElement>('circle.signal-node--b');
  if (!path) {
    path = document.createElementNS(NS, 'path');
    path.setAttribute('class', 'signal-path');
    svg.appendChild(path);
  }
  if (!a) {
    a = document.createElementNS(NS, 'circle');
    a.setAttribute('class', 'signal-node signal-node--a');
    a.setAttribute('r', '2.6');
    svg.appendChild(a);
  }
  if (!b) {
    b = document.createElementNS(NS, 'circle');
    b.setAttribute('class', 'signal-node signal-node--b');
    b.setAttribute('r', '2.6');
    svg.appendChild(b);
  }
  return { svg, path, a, b };
}

function card(): HTMLElement | null {
  return document.getElementById('source-card');
}

function hide(immediate = false) {
  active = null;
  window.clearTimeout(hideTimer);
  const t = layer();
  const c = card();
  if (t) {
    gsap.to([t.path, t.a, t.b], { opacity: 0, duration: immediate ? 0 : 0.16, overwrite: true });
  }
  if (c) gsap.to(c, { opacity: 0, duration: immediate ? 0 : 0.14, overwrite: true });
}

function placeCard(c: HTMLElement, cite: HTMLElement) {
  const r = cite.getBoundingClientRect();
  c.style.visibility = 'hidden';
  c.style.opacity = '0';
  c.style.left = '0px';
  c.style.top = '0px';
  const cw = c.offsetWidth;
  const ch = c.offsetHeight;
  const pad = 16;
  let left = r.left - 10;
  left = Math.max(pad, Math.min(left, window.innerWidth - cw - pad));
  let top = r.bottom + 12;
  if (top + ch > window.innerHeight - pad) top = r.top - ch - 12;
  top = Math.max(pad, top);
  c.style.left = `${left}px`;
  c.style.top = `${top}px`;
  c.style.visibility = 'visible';
}

function show(cite: HTMLElement) {
  const t = layer();
  const c = card();
  if (!t || !c) return;
  const videoId = cite.dataset.video || '';
  const row = videoId ? document.querySelector<HTMLElement>(`[data-video-row="${CSS.escape(videoId)}"]`) : null;
  if (!row) {
    hide();
    return;
  }
  const port = row.querySelector<HTMLElement>('[data-port]');
  if (!port || row.offsetParent === null || port.offsetParent === null) {
    hide();
    return;
  }

  active = cite;
  window.clearTimeout(hideTimer);

  const portRect = port.getBoundingClientRect();
  const citeRect = cite.getBoundingClientRect();
  const x1 = portRect.right + 2;
  const y1 = portRect.top + portRect.height / 2;
  const x2 = citeRect.left - 3;
  const y2 = citeRect.top + citeRect.height / 2;

  t.svg.setAttribute('viewBox', `0 0 ${window.innerWidth} ${window.innerHeight}`);
  const dx = Math.max(40, Math.abs(x2 - x1) * 0.3);
  const forward = x2 >= x1;
  const c1 = forward ? x1 + dx : x1 - dx;
  const c2 = forward ? x2 - dx : x2 + dx;
  const d = `M ${x1} ${y1} C ${c1} ${y1}, ${c2} ${y2}, ${x2} ${y2}`;
  t.path.setAttribute('d', d);
  t.a.setAttribute('cx', String(x1));
  t.a.setAttribute('cy', String(y1));
  t.b.setAttribute('cx', String(x2));
  t.b.setAttribute('cy', String(y2));

  const len = t.path.getTotalLength();
  const reduced = prefersReducedMotion();
  t.path.style.strokeDasharray = `${len}`;
  t.path.style.strokeDashoffset = reduced ? '0' : `${len}`;
  gsap.set([t.path, t.a, t.b], { opacity: 1 });
  if (!reduced) {
    gsap.to(t.path, { strokeDashoffset: 0, duration: 0.52, ease: 'power2.out', overwrite: true });
    gsap.fromTo(
      [t.a, t.b],
      { scale: 0, transformOrigin: 'center' },
      { scale: 1, duration: 0.35, ease: 'back.out(2)', delay: 0.06, overwrite: true },
    );
  }

  const index = c.querySelector<HTMLElement>('[data-card-index]');
  const time = c.querySelector<HTMLElement>('[data-card-time]');
  const title = c.querySelector<HTMLElement>('[data-card-title]');
  const snippet = c.querySelector<HTMLElement>('[data-card-snippet]');
  if (index) index.textContent = cite.dataset.index || '01';
  if (time) time.textContent = cite.dataset.time || '';
  if (title) title.textContent = cite.dataset.title || 'Source';
  if (snippet) snippet.textContent = cite.dataset.snippet || '';

  placeCard(c, cite);
  if (reduced) {
    c.style.opacity = '1';
  } else {
    gsap.fromTo(
      c,
      { opacity: 0, y: 6 },
      { opacity: 1, y: 0, duration: 0.36, ease: 'expo.out', overwrite: true },
    );
  }
}

export function startSignal() {
  if (started) return;
  started = true;

  const pick = (target: EventTarget | null) =>
    target instanceof Element ? target.closest<HTMLElement>('[data-cite]') : null;

  document.addEventListener('pointerover', (e) => {
    const cite = pick(e.target);
    if (cite) show(cite);
  });

  document.addEventListener('pointerout', (e) => {
    const cite = pick(e.target);
    if (!cite) return;
    const to = e.relatedTarget;
    if (to instanceof Node && cite.contains(to)) return;
    if (active === cite) hide();
  });

  document.addEventListener('focusin', (e) => {
    const cite = pick(e.target);
    if (cite) show(cite);
  });

  document.addEventListener('focusout', (e) => {
    const cite = pick(e.target);
    if (!cite) return;
    const to = e.relatedTarget;
    if (to instanceof Node && cite.contains(to)) return;
    if (active === cite) hide();
  });

  document.addEventListener('scroll', () => hide(), true);
  window.addEventListener('resize', () => hide());
}
