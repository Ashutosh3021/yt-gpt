from PIL import Image

from yt_gpt.vision.frames import build_contact_sheets, parse_scene_times, select_timestamps


def test_parse_scene_times_filters_out_of_range():
    stderr = "pts_time:0.500 pts_time:12.25 pts_time:99.0"
    assert parse_scene_times(stderr, 60) == [0.5, 12.25]


def test_select_timestamps_uses_scenes_and_falls_back():
    scenes = [60.0, 61.0, 120.0, 180.0, 240.0, 300.0]
    selected = select_timestamps(600, scenes)
    assert selected[0] == 0.5
    assert len(selected) >= 6
    assert all(0 <= value < 600 for value in selected)
    assert len(select_timestamps(60, [])) >= 6


def test_build_contact_sheets_chunks_frames(tmp_path):
    frames = []
    for index in range(7):
        path = tmp_path / f"frame_{index}.jpg"
        Image.new("RGB", (160, 90), (index * 20, 40, 80)).save(path)
        frames.append((float(index * 10), path))
    output = tmp_path / "sheets"
    sheets = build_contact_sheets(frames, output)
    assert len(sheets) == 2
    assert sheets[0]["frames"][0]["label"] == "00:00"
    assert (output / "sheet_001.jpg").is_file()
    assert (output / "sheet_002.jpg").is_file()
