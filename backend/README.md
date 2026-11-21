# yt-gpt backend

The FastAPI service, ingestion pipeline, retrieval engine and CLI that power the
`yt-gpt` package. The compiled frontend is bundled under
`src/yt_gpt/server/static` and served by the same process.

Install the published package and run it directly:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install yt-gpt
yt-gpt serve
```

Open <http://127.0.0.1:8765>. Cloning and `pip install -e ".[dev]"` are only
needed when developing the backend.

## Layout

```
src/yt_gpt/
├── cli.py              # yt-gpt serve | doctor | embed | export | version
├── config.py           # ~/.yt-gpt, config.toml, secret key
├── server/             # FastAPI app, routes, SSE, static bundle
├── auth/               # AuthProvider + local password profiles
├── workspace/          # atomic file store, models, transcripts.md export
├── ingest/             # URL normalisation, yt-dlp, captions, cleaning, chunking, jobs
├── retrieval/          # BM25 index + optional dense vectors + RRF
├── llm/                # LiteLLM wrapper, embeddings, prompts, context, chat, tools
├── vision/             # lazy scene sampling, contact sheets, exact frames
└── sources/            # reserved namespace; sources are stored by workspace/store.py
```

## Data

Everything lives under `~/.yt-gpt` (override with `YT_GPT_HOME`). There is no
database. `segments.jsonl` and `meta.json` are the source of truth; `clean.txt`,
`chunks.jsonl`, `vectors.npy` and `transcripts.md` are derived. `yt-gpt doctor
--rebuild` rebuilds text artifacts; `yt-gpt embed` rebuilds vectors.

API keys are stored in the OS keyring. If no keyring backend is available, a
`0600` file under `~/.yt-gpt/secrets/` is used instead.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy src
```

To run against the Vite dev server, build the frontend with
`VITE_API_MODE=http VITE_API_URL=http://127.0.0.1:8765 npm run build`, or run
`npm run dev` and keep the API on port 8765 (CORS for `localhost:5173` and
`127.0.0.1:5173` is enabled).

## Publishing

The workflow at `.github/workflows/autopublish.yml` is manually triggered with a
version string. It builds the frontend with `VITE_API_MODE=http`, bundles the
dist output, runs lint/type checks and the test suite, updates
`yt_gpt/version.py`, builds the wheel/sdist and publishes to PyPI. Configure a PyPI Trusted Publisher for this repository and workflow (or
add a `PYPI_API_TOKEN` repository secret as a fallback).

## Notes

- The server binds to `127.0.0.1` by default. Use `--host` only when you know
  what you are doing.
- Whisper is optional: `pip install "yt-gpt[whisper]"`.
- Visual analysis is lazy and opt-in. The workspace and session toggles default to
  off, text-only workspaces never download video, and frames require a vision-capable
  chat model.
- Retrieval is hybrid when an embedding model is configured: vector search is fused
  with BM25 using reciprocal rank fusion. Without vectors it falls back to BM25.
- License: MIT (see `LICENSE`).
