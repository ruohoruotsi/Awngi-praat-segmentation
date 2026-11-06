"""T2: generated grids are well-formed Praat TextGrids."""

import os


def _labeled(grid, tier):
    return [(iv.xmin, iv.xmax, str(iv.text)) for iv in grid[tier] if str(iv.text).strip()]


def test_master_grid_structure(seg_output):
    from pipeline.manifest import load_manifest
    from pipeline.textgrid import read_grid

    m = load_manifest(seg_output)
    grid = read_grid(os.path.join(seg_output, m["master_textgrid"]))
    assert list(grid.keys()) == ["Utterance", "Word", "Sound", "Events"]
    duration = m["source"]["duration_s"]
    for tier in grid.values():
        assert abs(float(tier[0].xmin)) < 1e-9
        assert abs(float(tier[-1].xmax) - duration) < 1e-6, (tier[-1].xmax, duration)
        # contiguity: each interval starts where the previous one ended
        for prev, cur in zip(tier, tier[1:]):
            assert abs(prev.xmax - cur.xmin) < 1e-9

    utt = _labeled(grid, "Utterance")
    assert len(utt) == len(m["segments"])
    for (a, b, label), seg in zip(utt, m["segments"]):
        assert abs(a - seg["start_s"]) < 1e-6 and abs(b - seg["end_s"]) < 1e-6
        # master scaffold uses short ids; clip files use the long id
        assert label == seg["id"].split("_t")[0] or label.startswith("seg_")


def test_clip_grids_rebased(seg_output):
    from pipeline.manifest import load_manifest
    from pipeline.textgrid import read_grid

    m = load_manifest(seg_output)
    for s in m["segments"][:8]:  # spot check a sample
        grid = read_grid(os.path.join(seg_output, s["textgrid"]))
        dur = s["end_s"] - s["start_s"]
        assert abs(float(grid["Utterance"][0].xmax) - dur) < 1e-6
        assert str(grid["Utterance"][0].text).strip() == s["id"]
        for tier in grid.values():
            assert abs(float(tier[0].xmin)) < 1e-9
            assert abs(float(tier[-1].xmax) - dur) < 1e-6


def test_grid_roundtrip(seg_output):
    """Write -> read must be lossless (Praat long format is our exchange format)."""
    from pipeline.manifest import load_manifest
    from pipeline.textgrid import read_grid, write_grid

    m = load_manifest(seg_output)
    grid = read_grid(os.path.join(seg_output, m["master_textgrid"]))
    path = os.path.join(seg_output, "roundtrip.TextGrid")
    write_grid(grid, path)
    back = read_grid(path)
    assert list(back.keys()) == list(grid.keys())
    for name in grid:
        a, b = grid[name], back[name]
        assert len(a) == len(b)
        for x, y in zip(a, b):
            assert abs(x.xmin - y.xmin) < 1e-9 and abs(x.xmax - y.xmax) < 1e-9
            assert str(x.text) == str(y.text)
