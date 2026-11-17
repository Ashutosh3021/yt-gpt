# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- Scene-change frame sampling, contact sheets and on-demand frame tools.
- Optional dense embeddings fused with BM25 retrieval.
- Map-reduce summaries and a cost/usage panel.

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

[Unreleased]: https://github.com/anomalyco/yt-gpt/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/anomalyco/yt-gpt/releases/tag/v0.1.0
