// Visible product copy lives here. The demo workspace is sample data and is marked in the UI.
// Assumptions:
// - The FastAPI server is not implemented in this repo yet; the demo runtime is the default.
// - Local auth is the only provider shown. Pyronites is a backend concern.
// - Provider and model ids in Settings are examples, not endorsements.
// - The production URL is the local address the package serves: http://127.0.0.1:8765
// - Demo transcript lines are written samples, not verbatim captions.

export const site = {
  name: 'yt-gpt',
  tagline: 'A local workspace for YouTube',
  description:
    'Turn YouTube links into clean transcripts and chat with them. Every answer cites the minute. Runs on your machine, with the model you choose.',
  url: 'http://127.0.0.1:8765',
  version: '1.0.0',
  root: '~/.yt-gpt',
  storagePath: '~/.yt-gpt/users/<you>/workspaces',
  colophon: 'Supreme by Fontshare, DM Mono by Google. Built with React, GSAP and Lenis.',
};

export const personas = [
  {
    id: 'default',
    name: 'Default',
    description: 'Clear, direct, cites the minute. No preamble.',
  },
  {
    id: 'skeptic',
    name: 'Skeptic',
    description: 'Questions the claim first. Marks what the videos do not support.',
  },
  {
    id: 'lecturer',
    name: 'Lecturer',
    description: 'Builds from first principles, one idea at a time.',
  },
  {
    id: 'editor',
    name: 'Editor',
    description: 'Tight sentences, active verbs, no filler.',
  },
  {
    id: 'custom',
    name: 'Custom',
    description: 'Your own system prompt, layered under the grounding rules.',
  },
] as const;

export const suggestedQuestions = [
  'What does attention actually do?',
  'Where do the videos disagree?',
  'Summarize the argument in five lines.',
  'What should I read next?',
];

export const providerModels: Record<string, string[]> = {
  openai: ['gpt-4.1-mini', 'gpt-4.1', 'o4-mini'],
  anthropic: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514'],
  google: ['gemini-2.5-flash', 'gemini-2.5-pro'],
  openrouter: ['openai/gpt-4.1-mini', 'anthropic/claude-sonnet-4'],
  ollama: ['llama3.2', 'qwen2.5:14b', 'mistral-small'],
  custom: ['your-model-id'],
};

export const emptyState = {
  workspaces: {
    title: 'No workspaces yet.',
    body: 'A workspace is a folder. Name it after the question you are trying to answer.',
  },
  videos: {
    title: 'The library is empty.',
    body: 'Paste links one per line. Captions are fetched first. Whisper runs only when a video has none.',
  },
  sessions: {
    title: 'Ask the room.',
    body: 'Answers cite the exact minute. Switch to interpretive mode when you want the model to reason beyond the videos.',
  },
  sources: {
    title: 'No sources yet.',
    body: 'The model can draft a note here and patch it later. Every save keeps a version.',
  },
};
