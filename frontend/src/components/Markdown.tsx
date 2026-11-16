import { useMemo } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import type { Video } from '../types';
import { formatTime } from './Timecode';

marked.setOptions({ gfm: true, breaks: true });

let hookInstalled = false;
function installHook() {
  if (hookInstalled) return;
  hookInstalled = true;
  DOMPurify.addHook('afterSanitizeAttributes', (node) => {
    if (node.tagName === 'A') {
      const href = node.getAttribute('href') || '';
      if (href.startsWith('http')) {
        node.setAttribute('target', '_blank');
        node.setAttribute('rel', 'noopener noreferrer');
      }
    }
  });
}

const esc = (s: string) =>
  s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

function snippetFor(video: Video | undefined, start: number): string {
  if (!video || !video.segments.length) return 'No transcript segment is available for this minute.';
  const seg =
    video.segments.find((s) => start >= s.start && start <= s.end) ??
    video.segments.reduce((best, s) => (Math.abs(s.start - start) < Math.abs(best.start - start) ? s : best), video.segments[0]);
  const text = seg.text.replace(/\s+/g, ' ').trim();
  return text.length > 170 ? `${text.slice(0, 167).trimEnd()}...` : text;
}

export function Markdown({
  content,
  videos = [],
  className = '',
}: {
  content: string;
  videos?: Video[];
  className?: string;
}) {
  const html = useMemo(() => {
    installHook();
    let i = 0;
    const cite = (rawId: string, start: number) => {
      i += 1;
      const video = videos.find((v) => v.id === rawId || v.youtubeId === rawId);
      const ytId = video?.youtubeId || rawId;
      const title = video?.title || 'Source not in this workspace';
      const time = formatTime(start);
      const snippet = snippetFor(video, start);
      const index = String(i).padStart(2, '0');
      const href = `https://youtu.be/${encodeURIComponent(ytId)}?t=${Math.max(0, Math.floor(start))}`;
      return `<a class="cite" href="${esc(href)}" target="_blank" rel="noopener noreferrer" data-cite data-video="${esc(
        video?.id || '',
      )}" data-start="${Math.floor(start)}" data-time="${esc(time)}" data-index="${index}" data-title="${esc(
        title,
      )}" data-snippet="${esc(snippet)}" aria-label="Source ${Number(index)}, ${time}, ${esc(
        title,
      )}. Opens on YouTube."><span class="cite__time">${time}</span><span class="cite__index" aria-hidden="true">${index}</span></a>`;
    };

    const withCites = content
      .replace(/\[\[cite:([\w-]+):(\d+)\]\]/g, (_m, id: string, start: string) => cite(id, Number(start)))
      .replace(/\[([A-Za-z0-9_-]{6,}) @ (\d+)(?::(\d+))?\]/g, (_m, id: string, a: string, b?: string) => {
        const start = b !== undefined ? Number(a) * 60 + Number(b) : Number(a);
        return cite(id, start);
      });

    const rendered = marked.parse(withCites, { async: false }) as string;
    return DOMPurify.sanitize(rendered, {
      ADD_ATTR: ['target', 'rel', 'data-cite', 'data-video', 'data-start', 'data-time', 'data-index', 'data-title', 'data-snippet'],
    });
  }, [content, videos]);

  return <div className={`prose ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
