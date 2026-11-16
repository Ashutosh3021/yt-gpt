import { useEffect } from 'react';
import { site } from '../data/site';

function setMeta(kind: 'name' | 'property', key: string, content: string) {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${kind}="${key}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(kind, key);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

function setCanonical(href: string) {
  let el = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!el) {
    el = document.createElement('link');
    el.setAttribute('rel', 'canonical');
    document.head.appendChild(el);
  }
  el.setAttribute('href', href);
}

export function PageMeta({ title, description, path }: { title: string; description: string; path?: string }) {
  useEffect(() => {
    const full = `${title} | ${site.name}`;
    document.title = full;
    const url = `${site.url}${path ?? window.location.pathname}`;
    setMeta('name', 'description', description);
    setMeta('property', 'og:title', full);
    setMeta('property', 'og:description', description);
    setMeta('property', 'og:url', url);
    setMeta('name', 'twitter:title', full);
    setMeta('name', 'twitter:description', description);
    setCanonical(url);
  }, [title, description, path]);
  return null;
}
