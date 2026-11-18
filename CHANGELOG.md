# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Map-reduce summaries and a cost/usage panel.
- Broader release hardening and clean-venv tests on every supported platform.

## [1.0.0] - 2026-11-18

### Added

- Optional visual pipeline: low-resolution video download, ffmpeg scene sampling,
  cached contact sheets and on-demand high-resolution frames.
- `get_contact_sheet` and `get_frame` tools with vision-capability gating and
  multimodal tool results.
- Workspace visual setting endpoint and a UI shortcut to enable visuals.
- Optional dense embeddings through the configured provider, stored per video as
  `vectors.npy` aligned with `chunks.jsonl`.
- Hybrid retrieval that fuses BM25 and cosine similarity with reciprocal rank
  fusion, falling back to BM25 when vectors are unavailable.
- Automatic embedding during ingest and `yt-gpt embed [workspace] [--force]` for
  existing workspaces.
- CI now checks formatting and verifies the committed frontend bundle.
- Manual publishing now runs lint, type checks and tests before uploading.

### Changed

- Version bump to 1.0.0.
- Documentation now describes hybrid retrieval and the opt-in visual pipeline.

## [0.1.0] - 2026-11-17

### Added

- Local password auth with signed HTTP-only session cookies.
- File-backed workspaces with atomic writes, safe paths, rename and trash.
- YouTube URL normalization, playlist expansion, yt-dlp metadata and caption ingestion.
- Manual, auto and Whisper caption waterfall with cleanup, chunking and timestamps.
- BM25 retrieval over transcript chunks.
- LiteLLM streaming chat with strict/interpretive grounding, personas and citations.
- Provider/model settings with keyring-backed API keys and Doctor checks.
- Chat sessions, Sources with version history, and Markdown transcript export.
- React web UI served from the Python package.
- CLI: `serve`, `doctor`, `export`, `version`.
- Manual PyPI publishing workflow with Trusted Publishing support.

[Unreleased]: https://github.com/anomalyco/yt-gpt/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/anomalyco/yt-gpt/releases/tag/v1.0.0
[0.1.0]: https://github.com/anomalyco/yt-gpt/releases/tag/v0.1.0
