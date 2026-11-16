"""BM25 retrieval with optional dense results merged through RRF."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .bm25 import BM25


def reciprocal_rank_fusion(
    rankings: Iterable[Iterable[dict[str, Any]]],
    *,
    k: int = 60,
    limit: int = 8,
) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    documents: dict[str, dict[str, Any]] = {}
    for ranking in rankings:
        for rank, document in enumerate(ranking):
            key = str(document.get("id") or f"{document.get('video_id')}:{document.get('start')}")
            documents.setdefault(key, document)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)[: max(1, limit)]
    merged: list[dict[str, Any]] = []
    for key, score in ordered:
        document = dict(documents[key])
        document["rrf"] = round(score, 6)
        merged.append(document)
    return merged


class Retriever:
    def __init__(self, chunks: Iterable[dict[str, Any]]) -> None:
        self.chunks = [dict(chunk) for chunk in chunks]
        self.index = BM25(self.chunks)

    @classmethod
    def from_store(cls, store: Any, ws_dir: Any) -> Retriever:
        return cls(store.all_chunks(ws_dir))

    def search(self, query: str, *, k: int = 8, video_ids: set[str] | None = None) -> list[dict[str, Any]]:
        return self.index.search(query, top_k=k, video_ids=video_ids)

    def search_hybrid(
        self,
        query: str,
        *,
        k: int = 8,
        video_ids: set[str] | None = None,
        dense: Iterable[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        keyword = self.search(query, k=max(k * 2, 10), video_ids=video_ids)
        if not dense:
            return keyword[:k]
        return reciprocal_rank_fusion([keyword, list(dense)], limit=k)
