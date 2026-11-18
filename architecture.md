# yt-gpt: Architecture

> A local, NotebookLM-style workspace for YouTube. Paste links, get transcripts (and optionally key visuals), then chat with the videos under per-session rules.

```
pip install yt-gpt
yt-gpt serve        # opens http://127.0.0.1:8765
```

---

## 1. Goals and non-goals

### Goals
- **Zero-setup install:** one `pip install`, one command, a browser UI on localhost.
- **Token-frugal by design:** reuse existing captions, clean them, retrieve only what a question needs, sample frames only when useful.
- **User-controlled LLM:** the user sets provider, API key and model in the UI. Any OpenAI-compatible endpoint (including Ollama) works.
- **Per-session control:** grounding mode (strict vs. interpretive), persona prompt, model override.
- **Everything is a file:** workspaces are plain folders the user can read, back up, grep or version-control.

### Non-goals (v1)
- No hosted/cloud service, no multi-device sync.
- No general database server (no Postgres/Mongo; no SQL engine at all).
- No non-YouTube sources (web pages, PDFs as primary sources) in v1. Uploaded docs are supported only in the Sources section.
- No video playback or editing inside the app.

---

## 2. System overview

```mermaid
flowchart LR
    U[User / Browser UI] -->|HTTP + SSE| API[FastAPI server]
    API --> AUTH[Auth provider]
    API --> WS[Workspace store (files)]
    API --> JOBS[Ingest job runner]
    API --> CHAT[Chat engine]

    JOBS --> META[yt-dlp: metadata]
    META --> CAP{Captions available?}
    CAP -->|manual| CLEAN
    CAP -->|auto only| CLEAN
    CAP -->|none| WHISPER[faster-whisper]
    WHISPER --> CLEAN[Clean + segment]
    CLEAN --> CHUNK[Chunk + index]
    CHUNK --> WS

    JOBS -.->|only if visuals enabled| VIS[Visual pipeline]
    VIS --> WS

    CHAT --> RET[Hybrid retrieval]
    RET --> WS
    CHAT --> LLM[LLM provider layer]
    CHAT --> TOOLS[Agent tools]
    TOOLS --> WS
    TOOLS --> VIS
```

Key difference from the original sketch: the pipeline is a **waterfall** (captions first, Whisper only as a fallback), not parallel branches. The visual pipeline is **lazy and opt-in**.

---

## 3. Package layout

```
yt_gpt/
├── cli.py                  # `yt-gpt serve | doctor | export | version`
├── config.py               # config dir, settings, defaults
├── server/
│   ├── app.py              # FastAPI app factory, middleware
│   ├── deps.py             # current user, workspace resolution
│   ├── sse.py              # server-sent events helpers
│   ├── routes/
│   │   ├── auth.py
│   │   ├── workspaces.py
│   │   ├── videos.py       # add links, status, delete
│   │   ├── sessions.py     # chat sessions + streaming
│   │   ├── sources.py      # docs CRUD, upload/download
│   │   └── settings.py     # provider / key / model
│   └── static/             # prebuilt frontend bundle (shipped in wheel)
├── auth/
│   ├── base.py             # AuthProvider protocol
│   ├── local.py            # local password profiles (default)
│   └── pyronites.py        # optional adapter (needs reachable backend)
├── workspace/
│   ├── store.py            # atomic file IO, locking, paths
│   ├── models.py           # pydantic models for on-disk JSON
│   └── export.py           # regenerate transcripts.md
├── ingest/
│   ├── urls.py             # normalize youtu.be / shorts / playlist
│   ├── metadata.py         # yt-dlp info extraction
│   ├── captions.py         # manual -> auto subtitle fetch
│   ├── whisper.py          # optional faster-whisper fallback
│   ├── clean.py            # strip tags, rolling duplicates, timestamps
│   ├── chunk.py            # timestamped chunking
│   └── jobs.py             # async queue, state machine, resume
├── vision/
│   ├── download.py         # low-res stream, section download
│   ├── scenes.py           # ffmpeg scene-change detection
│   ├── contact_sheet.py    # tile N thumbs into one image
│   └── frames.py           # on-demand high-res frame at timestamp
├── retrieval/
│   ├── bm25.py             # keyword index (in-memory, rebuilt from chunks)
│   ├── embeddings.py       # optional vectors (.npy), provider or local
│   └── hybrid.py           # reciprocal rank fusion
├── llm/
│   ├── provider.py         # LiteLLM wrapper, streaming
│   ├── capabilities.py     # vision? tools? context size? caching?
│   ├── prompts.py          # system prompts: strict / interpretive / persona
│   ├── context.py          # token-budgeted context assembly
│   ├── tools.py            # agent tool definitions + dispatch
│   └── chat.py             # the loop: retrieve -> answer -> tool calls
└── sources/
    ├── docs.py             # create / read / patch documents
    ├── patch.py            # find-replace edits, validation
    └── versions.py         # snapshot on every write
```

---

## 4. Storage: no database, just files

Root: `~/.yt-gpt/` (override with `YT_GPT_HOME`).

```
~/.yt-gpt/
├── config.toml                       # server port, auth provider, defaults
├── users/
│   └── <user_id>/
│       ├── profile.json              # display name, per-user settings (no secrets)
│       └── workspaces/
│           └── <workspace-slug>/
│               ├── workspace.json    # name, created_at, video order, settings
│               ├── transcripts.md    # GENERATED export (the "xyz.md")
│               ├── videos/
│               │   └── <video_id>/
│               │       ├── meta.json         # title, channel, duration, url, status
│               │       ├── segments.jsonl    # timestamped caption segments (source of truth)
│               │       ├── clean.txt         # LLM-ready text, sparse time markers
│               │       ├── summary.md        # optional map-reduce summary (cached)
│               │       ├── chunks.jsonl      # retrieval chunks with ranges
│               │       ├── vectors.npy       # optional embeddings (aligned to chunks)
│               │       └── visual/
│               │           ├── lowres.mp4    # deleted after scene detection (optional)
│               │           ├── keyframes/    # scene-change frames (jpg)
│               │           ├── sheets/       # contact sheets (jpg)
│               │           └── frames.json   # timestamps -> files
│               ├── sessions/
│               │   └── <session_id>.json     # settings + message history
│               └── sources/
│                   ├── <doc>.md
│                   └── .versions/<doc>/<timestamp>.md
└── secrets/                          # fallback only; keyring is preferred
```

### Why files work here
Data volume is small: even 500 videos produce tens of thousands of chunks, which fits in memory. BM25 is rebuilt from `chunks.jsonl` on workspace load (seconds), and cosine similarity over a `.npy` matrix with numpy is instant at that scale.

### Write rules
- **Atomic writes:** write to `*.tmp`, `fsync`, then `os.replace`.
- **Single-writer per workspace:** an in-process `asyncio.Lock` per workspace. Add a lockfile if multiple `serve` processes are ever allowed.
- **Derived vs. source-of-truth:** `segments.jsonl` and `meta.json` are authoritative. `clean.txt`, `chunks.jsonl`, `vectors.npy`, `summary.md` and `transcripts.md` are derived and can be regenerated (`yt-gpt doctor --rebuild`).
- **`transcripts.md` is regenerated**, never appended to, so it can't drift from the data.

### On-disk schemas

`meta.json`
```json
{
  "video_id": "dQw4w9WgXcQ",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "…",
  "channel": "…",
  "duration_s": 213,
  "language": "en",
  "transcript_source": "manual|auto|whisper",
  "status": "queued|fetching|transcribing|cleaning|indexing|ready|failed",
  "error": null,
  "added_at": "2026-11-15T10:00:00Z",
  "visual": { "enabled": false, "status": "none|queued|ready|failed" }
}
```

`segments.jsonl` (one JSON object per line)
```json
{"start": 12.4, "end": 15.9, "text": "so the key idea here is"}
```

`chunks.jsonl`
```json
{"chunk_id": "dQw4w9WgXcQ:0007", "video_id": "dQw4w9WgXcQ", "start": 300.0, "end": 372.5, "text": "…", "tokens": 480}
```

`sessions/<id>.json`
```json
{
  "session_id": "…",
  "title": "…",
  "created_at": "…",
  "settings": {
    "grounding": "strict|interpretive",
    "persona_id": "default|custom",
    "persona_prompt": null,
    "model_override": null,
    "use_visuals": false
  },
  "rolling_summary": "",
  "messages": [
    {"role": "user", "content": "…", "ts": "…"},
    {"role": "assistant", "content": "…", "citations": [{"video_id": "…", "start": 312}], "ts": "…"}
  ]
}
```

---

## 5. Ingestion pipeline

Triggered when the user pastes links (one per line). Each link becomes an independent job; one failure never blocks the others.

### 5.1 Steps (per video)

| # | Step | Detail |
|---|------|--------|
| 1 | **Normalize** | Extract video ID from `watch`, `youtu.be`, `shorts`, `live`; expand playlists into individual jobs; dedupe by ID against the workspace. |
| 2 | **Metadata** | `yt-dlp` info extraction only (no download). Store title, channel, duration, available subtitle tracks. |
| 3 | **Captions (waterfall)** | Prefer **manual** subtitles, then **auto-generated**, in the video's own language first, then English. Fetch in VTT/JSON3. No media download. |
| 4 | **Whisper fallback** | Only if no captions exist. Download audio only, run `faster-whisper` (optional extra) or a configured transcription API. Segments get timestamps. |
| 5 | **Clean** | Remove HTML tags and cue settings, collapse rolling duplicate lines from auto-captions, normalize whitespace, merge tiny fragments into sentences. Write `segments.jsonl` (with timestamps) and `clean.txt` (without per-line timestamps; a marker like `[mm:ss]` roughly every 30–60 s). |
| 6 | **Chunk** | Split on sentence boundaries into about 400–600 token chunks with about 50 token overlap. Each chunk keeps `start`/`end`. |
| 7 | **Index** | Add to BM25. If embeddings are enabled, embed chunks into `vectors.npy`. |
| 8 | **Export** | Regenerate `transcripts.md` for the workspace. |
| 9 | **(Optional) Summarize** | Map-reduce summary for long videos, cached in `summary.md`, keyed by `hash(transcript + model + prompt_version)`. |

### 5.2 State machine and resilience
```
queued -> fetching -> (transcribing) -> cleaning -> indexing -> ready
                  \________________________________________/-> failed (error recorded, retryable)
```
- **Resumable:** on restart, any job not in `ready`/`failed` resumes from its last completed step (steps are idempotent and artifacts are checked on disk).
- **Concurrency:** small worker pool (default 2 for network steps, 1 for Whisper) to avoid rate limits and CPU thrash.
- **Backoff:** exponential retry on transient errors (HTTP 429, network). Hard failures (private/removed video) are marked `failed` with a human-readable reason.
- **Progress:** each state change is pushed to the UI over SSE (`/api/workspaces/{id}/events`).

### 5.3 Cost preview
Before step 6, compute the transcript token count and show it in the UI ("about 18k tokens indexed; about $X to summarize with <model>"). Summarization and visual captioning are opt-in per workspace.

---

## 6. Visual pipeline (lazy, opt-in)

Runs only when `use_visuals` is on for the workspace or a session requests it. Text-only workspaces never download video.

```mermaid
flowchart TD
    A[Visual requested] --> B[Download low-res stream<br/>360p, no audio]
    B --> C[ffmpeg scene detection<br/>select='gt(scene,T)']
    C --> D[Cap + thin near-duplicates<br/>max 24 frames]
    D --> E[Sampled frames saved]
    E --> F[Build contact sheets<br/>6 thumbs / sheet, timestamp labels]
    F --> G[frames.json index]
    G -.->|LLM asks for detail| H[get_frame t=...<br/>download that section at high-res]
```

### Details
- **Scene detection:** `ffmpeg -vf "select='gt(scene,0.3)',showinfo"`. The threshold is tunable per video. If a video yields very few frames (talking head), add a minimum cadence (for example one frame per 2–3 minutes). If it yields too many (animation), raise the threshold and enforce a hard cap (default 24 frames per video).
- **Dedup:** scene timestamps closer than four seconds are thinned before extraction.
- **Contact sheets:** tile 6 keyframes (3×2) into one image with burned-in timestamps. The LLM browses sheets first; one sheet costs about the same as one image.
- **On-demand detail:** the LLM calls `get_frame(video_id, t)`. The server downloads only that time slice at higher resolution and extracts one frame. Results are cached in `visual/moments/`.
- **Trigger heuristics for the LLM:** the system prompt tells it to request a frame when the transcript references visuals ("as you can see", "this chart", "on the left") or when the user asks about on-screen content.
- **Capability gate:** if the chosen model has no vision or tool support, the visual tools are hidden and the UI explains why.
- **Cleanup:** the temporary download is deleted after frame extraction; only sampled frames, sheets and requested moments are kept.

---

## 7. Retrieval and context assembly

### 7.1 Hybrid retrieval
1. **BM25** over `chunks.jsonl` (always on).
2. **Embeddings** (optional): cosine similarity over `vectors.npy`. Provider embedding API or a local model via an optional extra.
3. **Reciprocal Rank Fusion** merges the two ranked lists. If embeddings are off, BM25 alone is used.
4. Optional **video filter** (user can scope a session to selected videos).

### 7.2 Context budget (per turn)
```
[system: rules + persona]                      <- cached by provider
[workspace manifest: id, title, duration,
 1-paragraph summary per video]                <- cached by provider
[rolling session summary]
[retrieved chunks, top-k within token budget]
[recent messages, last N turns verbatim]
[user question]
```
- **Full-context mode:** if the entire clean transcript set fits in about 60% of the model's context window, skip retrieval and send everything, relying on provider prompt caching so repeated turns are cheap.
- **Retrieval mode:** otherwise use the pipeline above.
- **Long sessions:** when history exceeds a threshold, summarize older turns into `rolling_summary`.

### 7.3 Citations
Chunks are labelled `[video_id @ mm:ss]`. The model must cite in that exact form; the UI turns citations into links (`https://youtu.be/<id>?t=<seconds>`).

---

## 8. Chat engine and agent tools

### 8.1 Loop
```
user message
  -> assemble context (7.2)
  -> LLM call (streaming)
       -> may emit tool calls (search, range, frame, source edits)
       -> server executes, appends results, continues (max N tool rounds)
  -> stream final answer + citations
  -> persist message + update rolling summary
```

### 8.2 Tools exposed to the LLM

| Tool | Purpose | Notes |
|------|---------|-------|
| `search_transcripts(query, video_ids?, k?)` | Extra retrieval mid-answer | Returns chunks with ranges |
| `get_transcript_range(video_id, start, end)` | Read an exact span | Hard cap on span length |
| `list_videos()` | Manifest | Cheap; also in system context |
| `get_contact_sheet(video_id, index)` | Browse visuals | Vision models only |
| `get_frame(video_id, t)` | High-res frame on demand | Vision models only; cached |
| `list_sources()` / `read_source(name)` | Access workspace docs | |
| `create_source(name, content)` | New doc | Snapshot version created |
| `patch_source(name, find, replace)` | Edit doc via find-replace | Rejects non-unique matches; snapshot first |

Patch-style edits keep token usage low and make every change reviewable and reversible.

### 8.3 Grounding modes (per session)

| Mode | Behaviour | Enforcement |
|------|-----------|-------------|
| **Strict** | Answer only from the videos; no outside knowledge or interpretation. | Strict system prompt; every claim needs a citation; **post-check** verifies cited `video_id`/timestamp exist (and that quoted text appears in the cited chunk, with fuzzy matching). If retrieval score is below threshold, return "not covered in these videos" instead of calling the model freely. |
| **Interpretive** | Model may reason, connect ideas and add its own knowledge, but marks what comes from the videos vs. its own inference. | Relaxed prompt; citations still encouraged. |

Strict mode is enforced by structure (required citations, verification, refusal on no evidence), but a prompt alone can never fully guarantee it, so the UI should say "strictly grounded", not "guaranteed".

### 8.4 Personas
A persona is a stored system-prompt fragment (built-in presets plus user-defined). It is layered **under** the grounding rules, so a persona cannot disable strict mode.

---

## 9. LLM provider layer

- **Library:** LiteLLM (or a thin OpenAI-compatible client) for a uniform interface across OpenAI, Anthropic, Google, OpenRouter, Ollama, etc.
- **User config (UI):** provider, API key, base URL (for local/OpenAI-compatible), chat model, optional embedding model. Stored per user.
- **Capabilities probe (`capabilities.py`):** for the chosen model, determine context size, tool-calling support, vision support and prompt-caching support. Unknown models get conservative defaults and a manual override toggle.
- **Streaming:** token streaming to the browser over SSE.
- **Secrets:** API keys go to the OS keyring (`keyring` library). Fallback is a `0600` file in `secrets/` with a visible warning in the UI. Keys are never written into workspace folders, logs, or exports.
- **Prompt caching:** mark the stable prefix (system + manifest) for providers that support explicit cache controls; order the prompt so the stable parts come first everywhere else.

---

## 10. Authentication

The login requirement is deliberately abstracted so the decision (see Section 15) doesn't block development.

```python
class AuthProvider(Protocol):
    async def sign_up(self, email: str, password: str) -> User: ...
    async def sign_in(self, email: str, password: str) -> User: ...
    async def sign_out(self, token: str) -> None: ...
    async def current_user(self, token: str) -> User | None: ...
```

| Provider | Setup | Use case |
|----------|-------|----------|
| `local` (default) | none | Local profiles; password hashed with argon2/bcrypt; stored in `~/.yt-gpt/users/`. Works offline. |
| `pyronites` (optional) | needs a reachable PyroCore backend URL + API key in config | Account-based login via the Pyronites client (`create_client()`, `client.auth.sign_in(...)`, `client.auth.user()`). |

- **Session:** after login the server issues a signed, HTTP-only, `SameSite=Strict` cookie. All routes except `/api/auth/*` and static assets require it.
- **Data isolation:** each user's data lives under `users/<user_id>/`; routes resolve paths from the authenticated user only (never from client-supplied paths).
- **Pyronites caveats:** the provider requires a running backend, so it breaks the offline, zero-setup flow if it's the only option. Any key shipped in a public package can be extracted, so use a key scoped to authentication only, or let each user supply their own backend URL and key.

---

## 11. HTTP API and frontend

### 11.1 Server
FastAPI + Uvicorn, bound to **127.0.0.1** by default.

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/auth/{signup,login,logout,me}` | POST/GET | Auth |
| `/api/workspaces` | GET/POST | List / create (name -> slug) |
| `/api/workspaces/{ws}` | GET/PATCH/DELETE | Read / rename / delete |
| `/api/workspaces/{ws}/videos` | POST | Body: newline-separated links |
| `/api/workspaces/{ws}/videos/{vid}` | GET/DELETE | Status / remove (re-exports transcript) |
| `/api/workspaces/{ws}/videos/{vid}/retry` | POST | Retry failed job |
| `/api/workspaces/{ws}/events` | GET (SSE) | Ingest progress |
| `/api/workspaces/{ws}/export` | GET | Download `transcripts.md` |
| `/api/workspaces/{ws}/sessions` | GET/POST | List / create session |
| `/api/workspaces/{ws}/sessions/{sid}` | GET/PATCH/DELETE | Settings, history |
| `/api/workspaces/{ws}/sessions/{sid}/messages` | POST (SSE stream) | Send message, stream reply |
| `/api/workspaces/{ws}/sources` | GET/POST | List / create or upload doc |
| `/api/workspaces/{ws}/sources/{name}` | GET/PUT/DELETE | Read / edit / delete (snapshots) |
| `/api/workspaces/{ws}/sources/{name}/versions` | GET | History / restore |
| `/api/settings/llm` | GET/PUT | Provider, key (write-only), model |

### 11.2 Frontend
- **Build:** prebuilt static bundle committed into the wheel, so end users never need Node. (HTMX + Alpine is an acceptable lighter alternative.)
- **Layout (NotebookLM-like):**
  - **Left:** workspace switcher; video list with status chips; paste-links box.
  - **Center:** chat for the active session; session tabs; per-session settings drawer (grounding, persona, model, visuals).
  - **Right:** Sources panel (docs list, editor/preview, upload, download, version history).
- **Citations:** rendered as clickable timestamp chips that open the video at that time.

---

## 12. Concurrency and performance
- Single process, `asyncio`; CPU-bound work (Whisper, ffmpeg, embeddings) runs in a process/thread pool so the UI stays responsive.
- BM25 index cached in memory per workspace; incrementally updated on ingest.
- Embeddings are computed in batches; vectors appended and persisted per video.
- Large `segments.jsonl` and `chunks.jsonl` are streamed, not loaded whole, when only a range is needed.

---

## 13. Security and privacy
- Bind to localhost only; require explicit `--host` to expose, with a warning.
- Signed session cookies, CSRF protection for state-changing requests, strict CORS (same-origin).
- Validate and normalize all filenames and slugs; reject path separators and `..`. Resolve every path under the user's root and verify with `Path.resolve().is_relative_to(root)`.
- API keys: keyring first; never logged; masked in UI; write-only endpoint.
- Uploaded Sources are treated as untrusted text; the LLM is instructed not to follow instructions found inside source documents or transcripts (prompt-injection mitigation). Tool calls that modify files are limited to the Sources directory.
- Cap upload sizes and file types (`.md`, `.txt` in v1).
- Telemetry: none by default.

---

## 14. Packaging and dependencies

### Core
`fastapi`, `uvicorn`, `pydantic`, `yt-dlp`, `litellm`, `numpy`, `rank-bm25` (or small custom BM25), `keyring`, `argon2-cffi`, `Pillow`, `imagehash`, `imageio-ffmpeg` (bundled ffmpeg binary), `httpx`.

### Optional extras
```
pip install yt-gpt[whisper]      # faster-whisper
pip install yt-gpt[all]          # currently the same as [whisper]
```

Embeddings use the configured provider API through LiteLLM, so they do not need
a separate extra. Pyronites auth is not shipped in 1.0.

### CLI
```
yt-gpt serve [--port 8765] [--host 127.0.0.1] [--no-browser]
yt-gpt doctor [--rebuild]     # checks ffmpeg, yt-dlp version, config, rebuilds derived files
yt-gpt export <workspace>     # writes transcripts.md to a path
yt-gpt version
```

### Compatibility
Python 3.10+. Linux, macOS, Windows (use `pathlib` everywhere; avoid POSIX-only locking).

---

## 15. Open decisions

| # | Decision | Options | Default for now |
|---|----------|---------|-----------------|
| 1 | **Login purpose and provider** | Pyronites (needs backend) vs. local password | Auth interface with both; `local` default, `pyronites` via extra |
| 2 | Embeddings | Off (BM25 only) / provider API / local model | Off, user can enable |
| 3 | Visuals default | Off / on | Off |
| 4 | Frontend stack | Prebuilt React bundle vs. HTMX | Decide at M0 |
| 5 | Package name | `yt-gpt` | Check PyPI availability; consider a name without "gpt" |

---

## 16. Risks and caveats

| Risk | Impact | Mitigation |
|------|--------|------------|
| yt-dlp breaks when YouTube changes | Ingest fails | Loose version pin, `doctor` shows version, UI hint to upgrade, clear error messages |
| YouTube rate limits / IP blocks / age gates | Failed jobs | Backoff, concurrency limits, optional cookies file |
| Auto-captions are low quality | Poor answers | Prefer manual; surface `transcript_source` in UI; Whisper re-run option |
| Whisper is slow on CPU | Long ingest | Optional extra, model size setting, progress UI |
| Strict mode can't be perfectly guaranteed | Trust | Citation verification + refusal on no evidence; honest UI wording |
| Provider differences (tools, vision, caching) | Broken features | Capability probe + feature gating |
| Pyronites backend dependency | Breaks zero-setup flow | Provider abstraction; local default |
| Terms of service for downloading from YouTube | Legal exposure | Personal, local use only; no redistribution; state clearly in docs |
