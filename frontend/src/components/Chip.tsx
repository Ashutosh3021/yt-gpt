import type { ReactNode } from 'react';
import type { Grounding, TranscriptSource, VideoStatus } from '../types';

const statusLabel: Record<VideoStatus, string> = {
  queued: 'Queued',
  fetching: 'Fetching',
  transcribing: 'Transcribing',
  cleaning: 'Cleaning',
  indexing: 'Indexing',
  ready: 'Ready',
  failed: 'Failed',
};

export function StatusChip({ status, dense = false }: { status: VideoStatus; dense?: boolean }) {
  return (
    <span className={`chip chip--status chip--${status}${dense ? ' chip--dense' : ''}`}>
      <span className="chip__led" aria-hidden="true" />
      {statusLabel[status]}
    </span>
  );
}

export function Badge({
  tone = 'neutral',
  children,
  title,
}: {
  tone?: 'neutral' | 'live' | 'warn' | 'fail' | 'signal';
  children: ReactNode;
  title?: string;
}) {
  return (
    <span className={`chip chip--${tone}`} title={title}>
      {children}
    </span>
  );
}

export function SourceBadge({ source }: { source: TranscriptSource }) {
  const label = source === 'manual' ? 'Manual captions' : source === 'auto' ? 'Auto captions' : 'Whisper';
  const tone = source === 'manual' ? 'live' : source === 'auto' ? 'warn' : 'neutral';
  return <Badge tone={tone}>{label}</Badge>;
}

export function GroundingChip({ grounding }: { grounding: Grounding }) {
  return (
    <span className={`chip chip--grounding chip--${grounding}`}>
      <span className="chip__led" aria-hidden="true" />
      {grounding === 'strict' ? 'Strictly grounded' : 'Interpretive'}
    </span>
  );
}
