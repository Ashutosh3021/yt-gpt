"""Optional dense vector indexing for transcript chunks."""

from __future__ import annotations

import logging
from typing import Any

from .provider import LlmConfig, embed_texts

log = logging.getLogger(__name__)


async def ensure_video_embeddings(
    store: Any,
    ws_dir: Any,
    video_id: str,
    config: LlmConfig,
    *,
    force: bool = False,
) -> int:
    """Embed one video's chunks when the configured model is not already indexed."""

    model = (config.embedding_model or "").strip()
    if not model:
        return 0
    chunks = store.read_chunks(ws_dir, video_id)
    if not chunks:
        return 0
    vectors, meta = store.read_vectors(ws_dir, video_id)
    if (
        not force
        and vectors is not None
        and str(meta.get("model") or "") == model
        and vectors.shape[0] == len(chunks)
    ):
        return 0
    texts = [str(chunk.get("text") or " ")[:20_000] for chunk in chunks]
    embedded = await embed_texts(config, texts)
    store.write_vectors(ws_dir, video_id, embedded, model)
    return len(embedded)


async def ensure_workspace_embeddings(
    store: Any,
    ws_dir: Any,
    config: LlmConfig,
    *,
    force: bool = False,
) -> int:
    """Embed any video chunks missing vectors for the configured model."""

    count = 0
    for video_dir in store.list_video_dirs(ws_dir):
        try:
            count += await ensure_video_embeddings(store, ws_dir, video_dir.name, config, force=force)
        except Exception as exc:
            log.warning("Embedding failed for %s: %s", video_dir.name, exc)
    return count
