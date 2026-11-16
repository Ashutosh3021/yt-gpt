# yt-gpt

**A local, NotebookLM-style workspace for YouTube.** Paste a list of video links, turn them into clean, searchable transcripts (and optionally key visuals), then chat with them. You choose the LLM, and each chat session has its own rules.

```bash
pip install yt-gpt
yt-gpt serve
```

> **Status: in design.** The package is not released yet, and the commands above describe the intended experience. See [`plan.md`](./plan.md) for the roadmap and [`architecture.md`](./architecture.md) for the technical design.

---

## The idea

![yt-gpt original flow diagram](./untitled.png)

The diagram above is the original sketch of the pipeline:

1. The user gives a **YouTube link**.
2. **yt-dlp** inspects the video.
3. If a **transcription already exists** (manual or auto captions), fetch it. Only if none exists, run **Whisper** (audio → text).
4. Optionally, **sample frames** from the video.
5. The LLM performs **multimodal analysis** over text (and frames) and answers the user.

The design refines the sketch in two ways: the transcript step is a *waterfall* (captions first, Whisper only as a fallback) instead of parallel branches, and frame sampling is *lazy and opt-in* so text-only workspaces never download video. Details are in [`architecture.md`](./architecture.md).

---

## What it will do

- **Workspaces:** log in, create a named workspace (e.g. `xyz`), and paste all your links, one per line:
  ```
  https://www.youtube.com/watch?v=...
  https://youtu.be/...
  https://www.youtube.com/playlist?list=...
  ```
- **Automatic ingestion:** captions are fetched and cleaned; Whisper runs only when a video has none. Live progress per link; one bad link never blocks the rest.
- **Raw transcript export:** the whole workspace is saved as `xyz.md` (regenerated whenever videos are added or removed).
- **Chat sessions:** create as many as you like inside a workspace, each with its own settings:
  - **Grounding mode:** *strict* (only what the videos say, no outside interpretation) or *interpretive* (the model may reason and add knowledge, clearly labelled).
  - **Persona:** built-in presets or your own personality prompt.
  - **Model override:** use a different model per session.
- **Sources section:** documents the LLM can create, edit (via small patches) and refine. You can download them, upload your own, and restore earlier versions.
- **Bring your own LLM:** set provider, API key and model in the UI. Any OpenAI-compatible endpoint works, including local models through Ollama.
- **Everything is a file:** no database. Your workspaces are plain folders you can read, back up or grep.

---

## How it keeps token usage low

| Area | Technique |
|------|-----------|
| Text | Reuse existing captions (never re-transcribe needlessly); strip tags, timestamps and rolling duplicate lines from auto-captions (about 20–30% fewer tokens) |
| Long videos | Chunk, retrieve only relevant chunks per question, cache per-video summaries |
| Frames | **Scene-change detection** instead of fixed intervals (static slides produce a handful of frames, not hundreds) |
| Frames | **Contact sheets:** tile 6 thumbnails into one image to browse many moments for the cost of one |
| Frames | **On-demand retrieval:** the model reads the transcript first and requests a high-res frame only when the speech points at something visual |
| Prompts | Stable prompt prefix ordering and provider prompt caching |

---

## Quick start (planned)

```bash
pip install yt-gpt              # core
pip install yt-gpt[whisper]     # + local Whisper fallback
pip install yt-gpt[embeddings]  # + local embeddings for semantic search
pip install yt-gpt[all]

yt-gpt serve                    # opens http://127.0.0.1:8765
```

1. Sign up / log in.
2. **Settings → LLM:** choose provider, enter your API key, pick a model.
3. **New workspace:** give it a name.
4. Paste your links (one per line) and wait for videos to reach *ready*.
5. **New session:** pick grounding mode and persona, then start chatting.
6. Use the **Sources** panel for documents the model drafts or you upload.

Other commands:

```bash
yt-gpt doctor [--rebuild]   # check ffmpeg / yt-dlp / config; rebuild derived files
yt-gpt export <workspace>   # write the workspace transcript to a file
yt-gpt version
```

---

## Where your data lives

```
~/.yt-gpt/
└── users/<user_id>/workspaces/xyz/
    ├── transcripts.md      # generated export of the whole workspace
    ├── videos/<id>/        # meta, timestamped segments, clean text, chunks, optional frames
    ├── sessions/           # one JSON file per chat session
    └── sources/            # documents (with version history)
```

Override the location with `YT_GPT_HOME`. API keys are stored in your OS keyring where available and never written into workspace folders.

---

## Privacy and security

- The server binds to **127.0.0.1** by default.
- Your videos, transcripts and chats stay on your machine; only the text/images needed for a question are sent to the LLM provider **you** configure.
- No telemetry by default.

---

## Limitations and notes

- **yt-dlp depends on YouTube's current behavior** and occasionally breaks; `yt-gpt doctor` will tell you when to upgrade it.
- **Auto-generated captions can be inaccurate;** the UI shows whether a transcript is manual, auto or Whisper-generated.
- **Strict mode is enforced structurally** (required timestamped citations, verification, refusal when nothing relevant is found), but no prompt can guarantee a model never strays.
- **Visual features** need a model that supports vision and tool calling.
- Use this tool for **personal, local use** and respect YouTube's Terms of Service and content creators' rights.

---

## Documentation

| File | Contents |
|------|----------|
| [`plan.md`](./plan.md) | Scope, milestones, testing strategy, risks, open decisions |
| [`architecture.md`](./architecture.md) | Components, pipeline, storage layout, retrieval, tools, API, security |
| [`untitled.png`](./untitled.png) | Original flow sketch |

---

## Roadmap

- **MVP:** login, workspaces, caption ingestion, retrieval, streaming chat with citations, sessions
- **v1.0:** Whisper fallback, Sources section, visual pipeline, embeddings, caching and cost panel, release hardening
- **Later:** per-session video filters, workspace import/export, more source types, optional sync

See [`plan.md`](./plan.md) for the full milestone breakdown.

---

## License

To be decided (MIT is the likely choice).
