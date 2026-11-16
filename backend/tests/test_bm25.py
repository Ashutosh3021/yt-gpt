from yt_gpt.retrieval.bm25 import BM25, tokenize
from yt_gpt.retrieval.hybrid import Retriever, reciprocal_rank_fusion

DOCUMENTS = [
    {
        "id": "a:0",
        "video_id": "videoA",
        "start": 0,
        "end": 30,
        "text": "The transformer uses attention to weigh every token in the sequence.",
    },
    {
        "id": "b:0",
        "video_id": "videoB",
        "start": 60,
        "end": 90,
        "text": "A convolutional network uses local filters and pooling.",
    },
    {
        "id": "c:0",
        "video_id": "videoC",
        "start": 120,
        "end": 150,
        "text": "Attention heads can specialize in syntax and coreference.",
    },
]


def test_tokenize_removes_stopwords_and_keeps_terms():
    assert tokenize("The attention is on the tokens") == ["attention", "tokens"]


def test_search_ranks_keyword_match_first():
    index = BM25(DOCUMENTS)
    results = index.search("attention tokens", top_k=3)
    assert results[0]["id"] in {"a:0", "c:0"}
    assert results[0]["score"] > results[-1].get("score", 0)


def test_search_can_filter_by_video():
    index = BM25(DOCUMENTS)
    results = index.search("attention", video_ids={"videoC"})
    assert [result["video_id"] for result in results] == ["videoC"]


def test_retriever_and_rrf():
    retriever = Retriever(DOCUMENTS)
    keyword = retriever.search("convolutional filters", k=2)
    assert keyword[0]["video_id"] == "videoB"

    dense = [{"id": "c:0", "video_id": "videoC", "text": "attention"}]
    merged = reciprocal_rank_fusion([keyword, dense], limit=3)
    assert {item["id"] for item in merged} == {"b:0", "c:0"}
