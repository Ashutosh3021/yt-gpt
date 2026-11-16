# yt-gpt: Build Plan

Companion to `architecture.md`. This document covers **what to build, in what order, and how to know each step is done**.

---

## 1. Product summary

`yt-gpt` is a pip-installable local web app: a NotebookLM-style workspace for YouTube. Users log in, create workspaces, paste video links, and chat with the content under per-session rules (strict vs. interpretive, personas), with a Sources section for LLM-editable documents.

```
pip install yt-gpt
yt-gpt serve
```

### Principles
1. **Text first, visuals later.** The transcript path must be solid before any video download.
2. **Cheap by default.** Reuse captions, clean them, retrieve instead of stuffing, cache prefixes.
3. **Everything is a file.** No database; derived data is always rebuildable.
4. **Ship a thin vertical slice early,** then deepen.
5. **Capability-gated features.** Don't break on models without vision, tools, or caching.

---

## 2. Scope

### MVP (Milestones 0–3)
- `pip install` + `yt-gpt serve`
- Login (local provider) and workspaces
- Paste links, caption-based ingestion with cleaning, progress UI
- `transcripts.md` export
- Hybrid-lite retrieval (BM25), streaming chat with citations
- Sessions with grounding mode and persona
- LLM provider/key/model settings

### v1.0 (Milestones 4–8)
- Whisper fallback, playlists, cookies, retries
- Sources section (create/edit/upload/download, versions, LLM tools)
- Visual pipeline (scene detection, contact sheets, on-demand frames)
- Embeddings, map-reduce summaries, prompt caching, cost preview
- Pyronites auth provider (if still wanted)
- Hardening, docs, release

### Later
- Selecting/filtering videos per session in the UI
- Export/import workspaces as zip
- Additional source types (PDF, web pages)
- Multi-workspace cross-search
- Optional sync

---

## 3. Milestones

Effort: **S** about 1–2 days, **M** about 3–5 days, **L** about 1–2 weeks (one developer).

### M0: Skeleton and CLI (S)
**Tasks**
- Repo, `pyproject.toml`, src layout, ruff + mypy + pytest, CI (lint + tests on Linux/macOS/Windows).
- `yt-gpt serve` starts FastAPI on `127.0.0.1:8765`, serves a placeholder page, opens the browser.
- Config directory (`~/.yt-gpt`, `YT_GPT_HOME`), `config.toml` loader.
- `yt-gpt doctor` checks Python version, ffmpeg (via `imageio-ffmpeg`), yt-dlp version.
- Decide frontend stack (prebuilt bundle vs. HTMX) and wire static serving from the wheel.

**Done when:** fresh venv → `pip install .` → `yt-gpt serve` shows a page; CI is green on all three OSes.

---

### M1: Auth and workspaces (M)
**Tasks**
- `AuthProvider` protocol; `LocalAuthProvider` (argon2 hashing, signed HTTP-only cookie).
- Auth routes + login/signup UI; auth middleware.
- Workspace store: atomic writes, slug generation, per-user root, path-safety helper (`resolve().is_relative_to`).
- Workspace CRUD routes and UI (create/rename/delete, list).
- *(If decided)* `PyronitesAuthProvider` behind the `[pyronites]` extra: config for URL/key, `sign_in`/`sign_up`/`current_user` mapping. Document the backend requirement.

**Done when:** two local users can't see each other's workspaces; path-traversal tests pass; deleting a workspace removes its folder.

---

### M2: Text ingestion (L)
**Tasks**
- URL normalizer (watch, youtu.be, shorts, live, playlist expansion, dedupe).
- Metadata via yt-dlp (no download); store `meta.json`.
- Caption waterfall: manual → auto; language preference; VTT/JSON3 parsing.
- Cleaning: strip tags/cue settings, collapse rolling duplicates, merge fragments, write `segments.jsonl` + `clean.txt` with sparse time markers.
- Chunker with timestamp ranges → `chunks.jsonl`.
- Async job runner: state machine, worker pool, resume-on-restart, retry with backoff, per-link failure isolation.
- SSE progress stream + UI video list with status chips and error messages.
- `transcripts.md` regeneration on add/remove.
- Token count + cost preview.

**Done when:** pasting 10 mixed links (some with manual captions, some auto, one private/removed) yields 9 ready videos, 1 clear failure, correct `transcripts.md`, and a restart mid-ingest resumes cleanly.

**Tests:** golden-file tests for caption cleaning (rolling duplicates are the main trap); mocked yt-dlp responses; job resume test.

---

### M3: Retrieval and chat (L)
**Tasks**
- BM25 index built from `chunks.jsonl`, cached in memory, incrementally updated.
- LLM settings UI + endpoints (provider, base URL, key write-only, model); keyring storage with fallback.
- LiteLLM wrapper with streaming; capability probe (context size, tools, vision, caching) with manual overrides.
- Context assembler: system + manifest + retrieved chunks + recent messages under a token budget; full-context mode when the corpus fits.
- Sessions: create/list/delete, history persistence, per-session settings (grounding, persona, model override).
- Prompts for strict and interpretive modes; persona layering; citation format `[video_id @ mm:ss]`.
- Chat UI with streaming, citation chips linking to `youtu.be/<id>?t=`.
- Strict-mode post-check: verify citations exist; refuse when retrieval is below threshold.

**Done when:** a user can ingest 3 videos, ask a question, get a streamed answer with working timestamp links; in strict mode an off-topic question returns "not covered"; in interpretive mode it answers and labels inference.

**Tests:** mocked LLM; citation-verification unit tests; retrieval relevance on a small fixed corpus.

> **MVP gate:** after M3, use it daily for a week on real videos before going further.

---

### M4: Robustness and Whisper (M)
**Tasks**
- Optional `[whisper]` extra: audio-only download, `faster-whisper`, model size setting, progress reporting.
- Whisper only when no captions exist; also a manual "re-transcribe with Whisper" action.
- Cookies file support (age-gated/members content), rate-limit backoff, concurrency settings.
- Playlist ingestion UI polish; bulk retry of failed items.
- `doctor --rebuild` regenerates all derived files from sources of truth.

**Done when:** a caption-less video ingests via Whisper end-to-end on CPU; rebuild reproduces identical derived files.

---

### M5: Sources section (M)
**Tasks**
- Sources store: create, read, update, delete; `.versions/` snapshot on every write.
- UI panel: list, markdown editor/preview, upload (`.md`/`.txt`), download, version history/restore.
- LLM tools: `list_sources`, `read_source`, `create_source`, `patch_source` (find-replace; reject non-unique or missing matches).
- Size/type limits, filename sanitization.
- Prompt-injection guard: sources/transcripts are data, not instructions.

**Done when:** the LLM can draft a summary doc, then revise one section via a patch; the user can undo via versions; uploads and downloads round-trip byte-for-byte.

---

### M6: Visual pipeline (L)
**Tasks**
- Low-res stream download; ffmpeg scene detection with tunable threshold.
- Frame cap, minimum cadence for static videos, perceptual-hash dedup.
- Contact sheets (6 per sheet, timestamp labels) and `frames.json` index.
- Tools: `get_contact_sheet`, `get_frame` (section download at high-res, cache).
- Prompt guidance for when to request visuals; capability gating (vision + tools).
- Cleanup of `lowres.mp4`; disk usage display.
- Per-workspace and per-session "use visuals" toggles.

**Done when:** on a slides-based 10-minute video, scene detection yields roughly 5–15 keyframes; the model answers a "what's on the slide at …" question by browsing a sheet then requesting one frame; text-only workspaces never download video.

**Benchmark to record:** tokens and cost with fixed-interval sampling vs. scene detection vs. scene detection + contact sheets + on-demand frames.

---

### M7: Token and cost optimization (M)
**Tasks**
- Provider prompt caching (stable prefix ordering; explicit cache markers where supported).
- Embeddings (optional): provider API or local `[embeddings]` extra; `vectors.npy`; RRF with BM25.
- Map-reduce summaries for long videos, cached by content+model+prompt hash; manifest summaries feed the system context.
- Rolling session summarization.
- Cost/usage panel: tokens per turn, estimated spend, cache hits.

**Done when:** measured token use on a 5-video workspace over a 20-turn session is documented before vs. after; cached turns show a clear drop.

---

### M8: Hardening and release (M)
**Tasks**
- Security pass: path safety, CSRF, cookie flags, key handling, upload limits, log scrubbing.
- Test matrix on Windows/macOS/Linux, Python 3.10–3.12; clean-venv install test.
- Docs: README (install, 5-minute tour), configuration, FAQ (yt-dlp updates, cookies, Whisper), limitations.
- Name check on PyPI and trademark sanity (consider alternatives to "gpt").
- Release automation with PyPI Trusted Publishing; semantic versioning; changelog.
- Error-message and empty-state polish; demo GIF.

**Done when:** `pip install yt-gpt` in a clean environment on each OS works end-to-end; a v0.1.0 tag publishes via CI.

---

## 4. Suggested order and dependencies

```
M0 ─> M1 ─> M2 ─> M3 ──(MVP gate)──> M4 ─┬─> M5 ─┐
                                         └─> M6 ─┼─> M7 ─> M8
```

M5 and M6 are independent after M3 and can be swapped. M7 benefits from M6's benchmarks, so do it afterwards.

---

## 5. Testing strategy

| Layer | Approach |
|-------|----------|
| Unit | Caption cleaning (golden VTT fixtures), URL normalization, chunking boundaries, patch tool, path safety, BM25 ranking, citation verification |
| Integration | Ingest pipeline with mocked yt-dlp; job resume after kill; chat loop with a fake LLM that emits tool calls |
| End-to-end | A small real-video smoke test (opt-in, network); optional Playwright UI test for login → create workspace → paste links → chat |
| Regression | Fixed mini-corpus + question set with expected cited timestamps, run on every retrieval change |
| Manual | Weekly dogfooding on real playlists; keep a log of failures to prioritize |

---

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| yt-dlp breakage after YouTube changes | High | Loose pin, `doctor` version check, clear UI error + upgrade hint, quick patch releases |
| Rate limiting / IP blocks | Medium | Low concurrency, backoff, cookies option |
| Poor auto-caption quality | Medium | Prefer manual; show transcript source; optional Whisper re-run |
| Model/provider feature drift (tools, vision, caching) | Medium | Capability probe + overrides + graceful degradation |
| Scope creep (NotebookLM has many features) | High | Hold the MVP gate; keep "Later" list out of v1 |
| Strict mode trust issues | Medium | Citation verification, refusal on no evidence, honest labeling |
| Pyronites backend requirement | Medium | Keep behind `AuthProvider`; local default |
| ToS concerns around downloading YouTube content | Medium | Personal local use only, no redistribution, document clearly |
| Windows quirks (paths, file locks, ffmpeg) | Medium | CI on Windows from M0, `pathlib` only |

---

## 7. Decisions needed from you

1. **What is login for?** Cross-machine accounts (needs a Pyronites backend and a restricted key) vs. keeping others out on a shared machine (local password is enough). This decides whether M1 includes the Pyronites adapter or defers it.
2. **Frontend stack:** prebuilt React bundle (richer UI, build step for you only) vs. HTMX/Alpine (simpler, smaller).
3. **Embeddings in v1?** Or ship BM25-only first and add embeddings in M7.
4. **Package name:** keep `yt-gpt` or pick one without "gpt".

---

## 8. First week checklist

- [ ] Create repo, `pyproject.toml`, CI (3 OSes)
- [ ] `yt-gpt serve` with placeholder page
- [ ] Config dir + `doctor`
- [ ] `AuthProvider` + local provider + login UI
- [ ] Workspace store with atomic writes and path-safety tests
- [ ] URL normalizer + yt-dlp metadata fetch on a few sample videos
- [ ] Capture 5 sample caption files (manual, auto, rolling-duplicate case) as test fixtures
