"""A compact BM25 index over transcript chunks."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+(?:['\u2019][a-z]+)?")

STOPWORDS = frozenset(
    """
    a an and are as at be been being but by can could did do does doing for from had has have having
    he her here hers herself him himself his how i if in into is it its itself just me might more most
    my myself no nor not of off on once only or other our ours ourselves out over own same she should so
    some such than that the their theirs them themselves then there these they this those through to too
    under until up very was we were what when where which while who whom why will with would you your
    yours yourself yourselves
    """.split()
)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in TOKEN_RE.finditer((text or "").lower()):
        token = match.group(0).replace("\u2019", "'")
        if len(token) < 2 and not token.isdigit():
            continue
        if token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens


class BM25:
    """Okapi BM25 with a small in-memory inverted index."""

    def __init__(self, documents: Iterable[dict[str, Any]], *, k1: float = 1.4, b: float = 0.72) -> None:
        self.documents: list[dict[str, Any]] = [dict(document) for document in documents]
        self.k1 = k1
        self.b = b
        self._postings: dict[str, list[tuple[int, int]]] = {}
        self._lengths: list[int] = []
        self._idf: dict[str, float] = {}

        for index, document in enumerate(self.documents):
            tokens = tokenize(str(document.get("text", "")))
            counts = Counter(tokens)
            self._lengths.append(len(tokens))
            for token, frequency in counts.items():
                self._postings.setdefault(token, []).append((index, frequency))

        total = len(self.documents)
        self._average_length = (sum(self._lengths) / total) if total else 0.0
        for token, postings in self._postings.items():
            frequency = len(postings)
            self._idf[token] = math.log(1.0 + (total - frequency + 0.5) / (frequency + 0.5))

    @property
    def size(self) -> int:
        return len(self.documents)

    def search(self, query: str, top_k: int = 8, video_ids: set[str] | None = None) -> list[dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens or not self.documents:
            return []
        scores: dict[int, float] = {}
        average = self._average_length or 1.0
        for token in dict.fromkeys(query_tokens):
            postings = self._postings.get(token)
            if not postings:
                continue
            idf = self._idf[token]
            for index, frequency in postings:
                document = self.documents[index]
                if video_ids and str(document.get("video_id")) not in video_ids:
                    continue
                length = self._lengths[index] or 1
                norm = self.k1 * (1.0 - self.b + self.b * length / average)
                scores[index] = scores.get(index, 0.0) + idf * frequency * (self.k1 + 1.0) / (
                    frequency + norm
                )

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[: max(1, top_k)]
        results: list[dict[str, Any]] = []
        for index, score in ranked:
            document = dict(self.documents[index])
            document["score"] = round(score, 5)
            results.append(document)
        return results
