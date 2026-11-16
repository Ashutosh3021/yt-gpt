# yt-gpt backend

The FastAPI service, ingestion pipeline, retrieval engine and CLI that power the
`yt-gpt` package. The compiled frontend is bundled under
`src/yt_gpt/server/static` and served by the same process.

```bash
pip install -e ".[dev]"
yt-gpt serve
```

Open <http://127.0.0.1:8765>.

## Layout

```
src/yt_gpt/
├── cli.py              # yt-gpt serve | doctor | export | version
├── config.py           # ~/.yt-gpt, config.toml, secret key
├── server/             # FastAPI app, routes, SSE, static bundle
├── auth/               # AuthProvider + local password profiles
├── workspace/          # atomic file store, models, transcripts.md export
├── ingest/             # URL normalisation, yt-dlp, captions, cleaning, chunking, jobs
├── retrieval/          # BM25 index (always on) + RRF helper
├── llm/                # LiteLLM wrapper, capabilities, prompts, context, chat, tools
├── vision/             # optional scene detection / contact sheets / frames
└── sources/            # document store + find/replace patch helper
```

## Data

Everything lives under `~/.yt-gpt` (override with `YT_GPT_HOME`). There is no
database. `segments.jsonl` and `meta.json` are the source of truth; `clean.txt`,
`chunks.jsonl`, `summary.md` and `transcripts.md` are derived and can be rebuilt
with `yt-gpt doctor --rebuild`.

API keys are stored in the OS keyring. If no keyring backend is available, a
`0600` file under `~/.yt-gpt/secrets/` is used instead.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

To run against the Vite dev server, build the frontend with
`VITE_API_MODE=http VITE_API_URL=http://127.0.0.1:8765 npm run build`, or run
`npm run dev` and keep the API on port 8765 (CORS for `localhost:5173` and
`127.0.0.1:5173` is enabled).

## Publishing

The workflow at `.github/workflows/autopublish.yml` is manually triggered with a
version string. It builds the frontend with `VITE_API_MODE=http`, bundles the
dist output, updates `yt_gpt/version.py`, builds the wheel/sdist and publishes to
PyPI. Configure a PyPI Trusted Publisher for this repository and workflow (or
add a `PYPI_API_TOKEN` repository secret as a fallback).

## Notes

- The server binds to `127.0.0.1` by default. Use `--host` only when you know
  what you are doing.
- Whisper is optional: `pip install "yt-gpt[whisper]"`.
- Visual tooling is optional in practice: the workspace/session toggles default
  to off, and text-only workspaces never download video.
