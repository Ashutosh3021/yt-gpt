from yt_gpt.ingest.chunk import chunk_segments
from yt_gpt.util import estimate_tokens


def make_segments(count: int = 12):
    segments = []
    for index in range(count):
        sentences = [
            f"Segment {index} sentence {part} explains one distinct part of the argument in enough detail to matter."
            for part in range(4)
        ]
        segments.append(
            {
                "start": index * 30.0,
                "end": index * 30.0 + 28.0,
                "text": " ".join(sentences),
            }
        )
    return segments


def test_chunks_are_bounded_and_labelled():
    chunks = chunk_segments("dQw4w9WgXcQ", make_segments())
    assert len(chunks) >= 2
    for index, chunk in enumerate(chunks):
        assert chunk["id"] == f"dQw4w9WgXcQ:{index:04d}"
        assert chunk["tokens"] <= 750
        assert chunk["start"] <= chunk["end"]
        assert chunk["text"]


def test_chunks_carry_overlap_and_cover_timestamps():
    segments = make_segments(16)
    chunks = chunk_segments("dQw4w9WgXcQ", segments)
    assert chunks[0]["start"] == 0
    assert chunks[-1]["end"] == segments[-1]["end"]
    last_sentence = chunks[0]["text"].split(". ")[-1].rstrip(".")
    assert last_sentence in chunks[1]["text"]


def test_short_tail_is_not_dropped():
    segments = [
        {
            "start": index * 10,
            "end": index * 10 + 9,
            "text": f"Segment {index} carries a reasonably detailed sentence with several words. " * 2,
        }
        for index in range(12)
    ]
    segments.append({"start": 120, "end": 130, "text": "Final short tail."})
    chunks = chunk_segments("dQw4w9WgXcQ", segments, target_tokens=100, min_tokens=200)
    assert chunks[-1]["end"] == 130
    assert "Final short tail." in chunks[-1]["text"]


def test_empty_input_returns_no_chunks():
    assert chunk_segments("dQw4w9WgXcQ", []) == []
    assert estimate_tokens("") == 0
