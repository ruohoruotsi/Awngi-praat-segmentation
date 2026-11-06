"""Measurement engine on synthetic data with known answers."""

import numpy as np
import pytest
import soundfile as sf
import textgrids

from pipeline.measure.extract import measure_grid
from pipeline.textgrid import _interval_tier


def make_wav(path, sr=44100, seconds=2.0):
    t = np.arange(int(sr * seconds)) / sr
    x = 0.5 * np.sin(2 * np.pi * 300 * t)
    sf.write(path, x.astype(np.float32), sr)
    return x, sr


def make_grid(sound_spans, event_spans):
    grid = textgrids.TextGrid()
    grid["Utterance"] = _interval_tier(2.0, [(0.5, 1.5, "seg_0001")])
    grid["Word"] = _interval_tier(2.0, [(0.4, 1.6, "kita")])
    grid["Sound"] = _interval_tier(2.0, sound_spans)
    grid["Events"] = _interval_tier(2.0, event_spans)
    return grid


def test_vot_and_closure_from_markers(tmp_path):
    x, sr = make_wav(str(tmp_path / "t.wav"))
    # markers 10 ms wide -> midpoints: CO 0.625, BR 0.675, VO 0.705
    grid = make_grid(
        sound_spans=[(0.60, 0.80, "t")],
        event_spans=[(0.62, 0.63, "CO"), (0.67, 0.68, "BR"), (0.70, 0.71, "VO")],
    )
    rows = measure_grid(grid, x, sr)
    assert len(rows) == 1
    row = rows[0]
    assert row["stop"] == "t"
    assert row["segment_id"] == "seg_0001"
    assert row["word"] == "kita"
    assert abs(row["closure_ms"] - 50.0) < 2.0, row["closure_ms"]   # BR-CO = 0.675-0.625
    assert abs(row["vot_ms"] - 30.0) < 2.0, row["vot_ms"]           # VO-BR = 0.705-0.675


def test_negative_vot_preserved(tmp_path):
    x, sr = make_wav(str(tmp_path / "t.wav"))
    # voicing onset BEFORE burst -> negative VOT (pre-voiced stop)
    grid = make_grid(
        sound_spans=[(0.60, 0.80, "d")],
        event_spans=[(0.62, 0.63, "CO"), (0.72, 0.73, "BR"), (0.69, 0.70, "VO")],
    )
    row = measure_grid(grid, x, sr)[0]
    assert abs(row["vot_ms"] - (-30.0)) < 2.0, row["vot_ms"]


def test_missing_markers_yield_empty_cells(tmp_path):
    x, sr = make_wav(str(tmp_path / "t.wav"))
    grid = make_grid(
        sound_spans=[(0.60, 0.80, "k")],
        event_spans=[(0.62, 0.63, "CO")],
    )
    row = measure_grid(grid, x, sr)[0]
    assert row["closure_ms"] is None
    assert row["vot_ms"] is None
    assert row["spec_centroid_hz"] is None


def test_spectral_features_shape(tmp_path):
    # 2 kHz tone -> centroid should sit near 2 kHz
    t = np.arange(44100 * 2) / 44100
    x = 0.5 * np.sin(2 * np.pi * 2000 * t).astype(np.float32)
    sf.write(str(tmp_path / "tone.wav"), x, 44100)
    grid = make_grid(
        sound_spans=[(0.60, 0.80, "k")],
        event_spans=[(0.62, 0.63, "CO"), (0.67, 0.68, "BR"), (0.70, 0.71, "VO")],
    )
    row = measure_grid(grid, x, 44100)
    assert len(row) > 0
    r = row[0]
    assert r["spec_centroid_hz"] is not None
    assert abs(r["spec_centroid_hz"] - 2000.0) < 250.0, r["spec_centroid_hz"]
    assert len([k for k in r if k.startswith("c") and k[1:3].isdigit()]) == 12
    assert all(isinstance(r["c%02d" % i], float) for i in range(12))


def test_burst_estimate_finds_transient(tmp_path):
    sr = 44100
    x = np.zeros(sr * 2, dtype=np.float32)
    # quiet, then a 30 ms broadband transient at 0.67 s (the "burst")
    i0, i1 = int(0.67 * sr), int(0.70 * sr)
    x[i0:i1] = np.random.default_rng(0).normal(0, 0.5, i1 - i0)
    grid = make_grid(
        sound_spans=[(0.60, 0.80, "t")],
        event_spans=[(0.62, 0.63, "CO"), (0.67, 0.68, "BR"), (0.70, 0.71, "VO")],
    )
    row = measure_grid(grid, x, sr)[0]
    assert row["burst_ms_est"] is not None
    assert 15.0 < row["burst_ms_est"] < 80.0, row["burst_ms_est"]
