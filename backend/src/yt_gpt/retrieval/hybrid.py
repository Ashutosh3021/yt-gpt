"""BM25 retrieval with optional dense results merged through RRF."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import numpy.typing as npt

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
    def __init__(
        self,
        chunks: Iterable[dict[str, Any]],
        *,
        dense_chunks: Iterable[dict[str, Any]] | None = None,
        dense_vectors: Any = None,
        dense_model: str | None = None,
    ) -> None:
        self.chunks = [dict(chunk) for chunk in chunks]
        self.index = BM25(self.chunks)
        self.dense_chunks = [dict(chunk) for chunk in dense_chunks or []]
        matrix = np.asarray(dense_vectors, dtype=np.float32) if dense_vectors is not None else None
        if matrix is not None and (matrix.ndim != 2 or matrix.shape[0] != len(self.dense_chunks)):
            matrix = None
        self.dense_matrix = matrix
        self.dense_model = dense_model
        self._query_vector: np.ndarray | None = None

    @classmethod
    def from_store(cls, store: Any, ws_dir: Any, embedding_model: str | None = None) -> Retriever:
        chunks = store.all_chunks(ws_dir)
        if not embedding_model:
            return cls(chunks)
        dense_chunks, matrix = store.load_dense_chunks(ws_dir, embedding_model)
        return cls(chunks, dense_chunks=dense_chunks, dense_vectors=matrix, dense_model=embedding_model)

    @property
    def has_dense(self) -> bool:
        return self.dense_matrix is not None and len(self.dense_chunks) > 0

    def set_query_vector(self, vector: Iterable[float] | None) -> None:
        if vector is None:
            self._query_vector = None
            return
        array = np.asarray([float(value) for value in vector], dtype=np.float32)
        norm = float(np.linalg.norm(array))
        self._query_vector = array / norm if norm > 0 else None

    def _dense_results(self, *, top_k: int, video_ids: set[str] | None = None) -> list[dict[str, Any]]:
        if self.dense_matrix is None or self._query_vector is None:
            return []
        matrix = self.dense_matrix
        if matrix.shape[1] != self._query_vector.shape[0]:
            return []
        scores = matrix @ self._query_vector
        allowed: npt.NDArray[np.bool_] = np.ones(len(self.dense_chunks), dtype=bool)
        if video_ids:
            allowed = np.asarray(
                [str(chunk.get("video_id")) in video_ids for chunk in self.dense_chunks], dtype=bool
            )
        scores = np.where(allowed, scores, -np.inf)
        order = [int(index) for index in np.argsort(-scores)[: max(1, top_k)]]
        results: list[dict[str, Any]] = []
        for index in order:
            score = float(scores[index])
            if not np.isfinite(score):
                continue
            chunk = dict(self.dense_chunks[index])
            chunk["dense_score"] = round(score, 6)
            results.append(chunk)
        return results

    def search(self, query: str, *, k: int = 8, video_ids: set[str] | None = None) -> list[dict[str, Any]]:
        keyword = self.index.search(query, top_k=max(k * 2, 10), video_ids=video_ids)
        dense = self._dense_results(top_k=max(k * 2, 10), video_ids=video_ids)
        if not dense:
            return keyword[:k]
        return reciprocal_rank_fusion([keyword, dense], limit=k)

    def search_hybrid(
        self,
        query: str,
        *,
        k: int = 8,
        video_ids: set[str] | None = None,
        dense: Iterable[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        keyword = self.index.search(query, top_k=max(k * 2, 10), video_ids=video_ids)
        if dense is None:
            dense = self._dense_results(top_k=max(k * 2, 10), video_ids=video_ids)
        if not dense:
            return keyword[:k]
        return reciprocal_rank_fusion([keyword, list(dense)], limit=k)
