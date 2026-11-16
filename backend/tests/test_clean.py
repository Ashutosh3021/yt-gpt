from yt_gpt.ingest.captions import parse_json3, parse_vtt
from yt_gpt.ingest.clean import clean_segments, normalize_text, render_clean_text


def test_normalize_text_strips_markup_and_html_entities():
    assert normalize_text("<v Ada>Hello&nbsp; world</v>") == "Hello world"


def test_parse_vtt_handles_settings_and_tags():
    payload = """WEBVTT

00:00:01.000 --> 00:00:03.500 align:start position:0%
<v Ada>Hello there</v>

00:00:03.500 --> 00:00:05.000
General Kenobi
"""
    segments = parse_vtt(payload)
    assert segments[0]["start"] == 1.0
    assert segments[0]["text"] == "Hello there"
    assert segments[1]["text"] == "General Kenobi"


def test_parse_json3():
    payload = '{"events":[{"tStartMs":1000,"dDurationMs":2000,"segs":[{"utf8":"Hello "},{"utf8":"world"}]}]}'
    segments = parse_json3(payload)
    assert segments == [{"start": 1.0, "end": 3.0, "text": "Hello world"}]


def test_rolling_captions_are_collapsed():
    raw = [
        {"start": 0, "end": 2, "text": "the key idea"},
        {"start": 2, "end": 4, "text": "the key idea is simple"},
        {"start": 4, "end": 6, "text": "is simple and useful"},
        {"start": 6, "end": 8, "text": "[Music]"},
    ]
    cleaned = clean_segments(raw)
    text = " ".join(segment["text"] for segment in cleaned)
    assert text == "the key idea is simple and useful"
    assert "[Music]" not in text


def test_render_clean_text_inserts_sparse_markers():
    segments = [
        {"start": 0, "end": 2, "text": "First sentence."},
        {"start": 60, "end": 62, "text": "Second sentence."},
    ]
    rendered = render_clean_text(segments)
    assert rendered.startswith("[00:00] First sentence.")
    assert "[01:00] Second sentence." in rendered
