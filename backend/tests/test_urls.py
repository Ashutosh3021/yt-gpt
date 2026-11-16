from yt_gpt.ingest.urls import extract_video_id, normalize_links, playlist_url


def test_extract_common_video_urls():
    expected = "dQw4w9WgXcQ"
    assert extract_video_id(expected) == expected
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == expected
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=42") == expected
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == expected
    assert extract_video_id("youtube.com/live/dQw4w9WgXcQ") == expected
    assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == expected


def test_rejects_non_youtube_and_bad_ids():
    assert extract_video_id("https://vimeo.com/123456") is None
    assert extract_video_id("https://example.com/watch?v=dQw4w9WgXcQ") is None
    assert extract_video_id("") is None


def test_playlist_detection():
    url = "https://www.youtube.com/playlist?list=PL1234567890"
    assert playlist_url(url) == url
    assert playlist_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890") is None


def test_normalize_links_deduplicates_and_reports_invalid():
    text = """
    https://youtu.be/dQw4w9WgXcQ
    https://www.youtube.com/watch?v=dQw4w9WgXcQ
    https://www.youtube.com/playlist?list=PL123
    not a video
    """
    result = normalize_links(text)
    assert result.video_ids == ["dQw4w9WgXcQ"]
    assert result.playlist_urls == ["https://www.youtube.com/playlist?list=PL123"]
    assert result.invalid == ["not a video"]
