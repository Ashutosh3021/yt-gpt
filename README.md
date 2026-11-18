# yt-gpt

**A local, NotebookLM-style workspace for YouTube.** Paste video or playlist links, turn them into clean, searchable transcripts, then chat with them under per-session rules. You choose the LLM, and everything is stored as plain files on your machine.

```bash
pip install yt-gpt
yt-gpt serve
```

> **Status: 1.0.** Caption ingestion, Whisper fallback, hybrid BM25 + dense retrieval, streaming chat with citations, sessions, Sources, optional visual frames and the local web UI are implemented.

---

## What it does

- **Workspaces:** create a named workspace and paste links, one per line:
  ```
  https://www.youtube.com/watch?v=...
  https://youtu.be/...
  https://www.youtube.com/playlist?list=...
  ```
- **Caption ingestion:** manual captions are preferred, auto-captions are cleaned and deduplicated, and Whisper runs only when a video has no captions and the `[whisper]` extra is installed. Live per-link progress; one bad link does not block the rest.
- **Transcript export:** each workspace keeps `transcripts.md` up to date as videos are added or removed.
- **Chat sessions:** each session has its own grounding mode (*strict* or *interpretive*), persona and optional model override.
- **Citations:** answers can cite `[video_id @ mm:ss]`, rendered as timestamped YouTube links in the UI.
- **Sources:** documents the LLM can create, patch and refine, with version history, upload and download.
- **Bring your own LLM:** OpenAI, Anthropic, Google, OpenRouter, Ollama or any OpenAI-compatible endpoint. Keys are stored in the OS keyring when available. Optionally choose an embedding model (Anthropic does not expose one) to fuse dense retrieval with BM25.
- **Visual questions:** opt in per workspace and session, then use a vision-capable model to inspect cached contact sheets and request exact high-resolution frames. Text-only workspaces never download video.
- **Everything is a file:** no database. Workspaces are folders you can read, back up or grep.

---

## Quick start

```bash
pip install yt-gpt              # core
pip install "yt-gpt[whisper]"   # + local Whisper fallback
pip install "yt-gpt[all]"       # currently the same as [whisper]

yt-gpt serve                    # http://127.0.0.1:8765
```

1. Sign up / log in.
2. **Settings → LLM:** choose provider, enter your API key and pick a model. Add an embedding model if you want dense retrieval.
3. **New workspace:** give it a name.
4. Paste your links and wait for videos to reach *ready*. New ingests build vectors automatically when an embedding model is configured; run `yt-gpt embed` once for older workspaces.
5. **New session:** choose grounding mode and persona, then start chatting. Enable visuals per workspace and session if the model supports vision.
6. Use the **Sources** panel for documents the model drafts or you upload.

Other commands:

```bash
yt-gpt doctor [--rebuild]   # check ffmpeg / yt-dlp / config; rebuild derived files
yt-gpt embed [workspace]    # build dense vectors for existing workspaces
yt-gpt export <workspace>   # write the workspace transcript to a file
yt-gpt version
```

---

## How it keeps token usage low

| Area | Technique |
|------|-----------|
| Text | Reuse existing captions; strip tags, timestamps and rolling duplicate lines from auto-captions |
| Retrieval | BM25 over timestamped chunks, fused with dense vectors when an embedding model is configured |
| Visuals | Lazy, opt-in contact sheets from sampled frames; exact frames only when requested |
| Context | Recent session history capped by message and character limits; retrieved passages sized to the model context |
| Prompts | Stable prompt prefix ordering keeps the system and evidence prefix consistent |

---

## Where your data lives

```
~/.yt-gpt/
└── users/<user_id>/workspaces/<workspace>/
    ├── workspace.json      # workspace metadata
    ├── transcripts.md      # generated export of the whole workspace
    ├── videos/<id>/        # meta, segments, chunks, vectors, optional visual cache
    ├── sessions/           # one JSON file per chat session
    └── sources/            # documents with version history
```

Override the location with `YT_GPT_HOME`. Secrets are never written into workspace folders.

---

## Privacy and security

- The server binds to **127.0.0.1** by default.
- Videos, transcripts and chats stay on your machine; only the text and optional sampled frames needed for a question are sent to the LLM provider **you** configure.
- No telemetry.
- Sessions use signed, HTTP-only cookies.

---

## Limitations

- **yt-dlp depends on YouTube's current behavior** and occasionally breaks; `yt-gpt doctor` reports the installed version.
- **Auto-generated captions can be inaccurate.** The UI shows whether a transcript is manual, auto or Whisper-generated.
- **Strict mode is enforced structurally** with required citations and refusal when retrieval is empty, but no prompt can guarantee a model never strays.
- **Visuals are sampled, not full video analysis.** Contact sheets are built lazily from scene changes and capped at 24 frames; exact frames are cached on demand.
- **Dense retrieval is optional.** It requires an embedding model and either a fresh ingest or one `yt-gpt embed` run. BM25 remains the fallback.
- **Visual tools need a vision-capable model.** The toggles stay disabled when the selected model does not report vision support.
- Use this tool for **personal, local use** and respect YouTube's Terms of Service and content creators' rights.

---

## Documentation

| File | Contents |
|------|----------|
| [`plan.md`](./plan.md) | Scope, milestones, testing strategy, risks, open decisions |
| [`architecture.md`](./architecture.md) | Components, pipeline, storage layout, retrieval, tools, API, security |
| [`backend/README.md`](./backend/README.md) | Backend layout, development and publishing |
| [`CHANGELOG.md`](./CHANGELOG.md) | Release notes |
| [`untitled.png`](./untitled.png) | Original flow sketch |

---

## Roadmap

- **Done:** local auth, workspaces, caption ingestion, playlist expansion, Whisper fallback, hybrid retrieval, streaming chat with citations, sessions, Sources with versions, optional visual frames, CLI, bundled web UI, CI and PyPI publishing.
- **Next:** map-reduce summaries, cost/usage panel, broader release hardening and clean-venv tests on all supported platforms.
- **Later:** per-session video filters, workspace zip import/export, additional source types, cross-workspace search, optional sync.

---

## License

MIT. See [`LICENSE`](./LICENSE).
