"""Validate/lint behaviour on synthetic grids."""

import textgrids

from pipeline.textgrid import _interval_tier
from pipeline.validate import validate_grid


def make_grid(sound_spans, event_spans, word_spans=None):
    grid = textgrids.TextGrid()
    grid["Utterance"] = _interval_tier(10.0, [(0.0, 10.0, "seg_0001")])
    grid["Word"] = _interval_tier(10.0, word_spans or [])
    grid["Sound"] = _interval_tier(10.0, sound_spans)
    grid["Events"] = _interval_tier(10.0, event_spans)
    return grid


def good_grid():
    # stop "t" at 4.0-4.5: CO 4.02-4.03, BR 4.30-4.31, VO 4.38-4.39
    return make_grid(
        sound_spans=[(4.0, 4.5, "t")],
        event_spans=[(4.02, 4.03, "CO"), (4.30, 4.31, "BR"), (4.38, 4.39, "VO")],
        word_spans=[(3.5, 5.0, "kita")],
    )


def test_good_grid_clean():
    issues = validate_grid(good_grid())
    errors = [i for i in issues if i["severity"] == "error"]
    assert not errors, errors


def test_missing_marker_flagged():
    grid = make_grid(
        sound_spans=[(4.0, 4.5, "t")],
        event_spans=[(4.02, 4.03, "CO"), (4.30, 4.31, "BR")],  # no VO
    )
    msgs = [i["message"] for i in validate_grid(grid)]
    assert any("no VO marker" in m for m in msgs), msgs


def test_co_after_br_flagged():
    grid = make_grid(
        sound_spans=[(4.0, 4.5, "t")],
        event_spans=[(4.30, 4.31, "CO"), (4.02, 4.03, "BR"), (4.38, 4.39, "VO")],
    )
    # markers are matched by label position inside the stop; CO mid > BR mid
    issues = validate_grid(grid)
    assert any("must precede" in i["message"] for i in issues), issues


def test_unknown_label_flagged():
    grid = make_grid(
        sound_spans=[(4.0, 4.5, "t")],
        event_spans=[(4.02, 4.03, "XX"), (4.30, 4.31, "BR"), (4.38, 4.39, "VO")],
    )
    issues = validate_grid(grid)
    assert any("unknown Events label" in i["message"] for i in issues), issues


def test_wide_marker_warned():
    grid = make_grid(
        sound_spans=[(4.0, 5.5, "t")],
        event_spans=[(4.02, 4.60, "CO"), (4.30, 4.31, "BR"), (4.38, 4.39, "VO")],
    )
    issues = validate_grid(grid)
    assert any("wide" in i["message"] for i in issues), issues


def test_stop_outside_word_warned():
    grid = make_grid(
        sound_spans=[(4.0, 4.5, "t")],
        event_spans=[(4.02, 4.03, "CO"), (4.30, 4.31, "BR"), (4.38, 4.39, "VO")],
        word_spans=[(6.0, 7.0, "kita")],  # word far away
    )
    issues = validate_grid(grid)
    assert any("outside any labelled Word" in i["message"] for i in issues), issues
