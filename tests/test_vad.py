"""T1: segmentation correctness + determinism on real data."""

import os


def test_segments_structural(seg_output):
    from pipeline.manifest import load_manifest

    m = load_manifest(seg_output)
    segs = [(s["start_s"], s["end_s"]) for s in m["segments"]]
    assert len(segs) > 30, "expected a long recording to yield many segments"
    duration = m["source"]["duration_s"]
    prev_end = -1.0
    for start, end in segs:
        assert 0.0 <= start < end <= duration
        assert start > prev_end + 1e-6, "segments must not overlap"
        prev_end = end


def test_vad_deterministic(seg_output):
    import os

    from pipeline.manifest import load_manifest
    from pipeline.vad import load_model, run_vad

    audio = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "audio", "1203_spm37_intervocalic.WAV")
    m = load_manifest(seg_output)
    first = [(s["start_s"], s["end_s"]) for s in m["segments"]]
    model = load_model()
    second = run_vad(audio, model, pad_ms=m["params"]["pad_ms"],
                     min_speech_ms=m["params"]["min_speech_ms"],
                     threshold=m["params"]["threshold"])
    assert len(second) == len(first)
    for (a1, b1), (a2, b2) in zip(first, second):
        assert abs(a1 - a2) < 1e-9 and abs(b1 - b2) < 1e-9


def test_clips_exist_and_match(seg_output):
    import soundfile as sf

    from pipeline.manifest import load_manifest

    m = load_manifest(seg_output)
    for s in m["segments"]:
        clip = os.path.join(seg_output, s["clip"])
        grid = os.path.join(seg_output, s["textgrid"])
        assert os.path.exists(clip), clip
        assert os.path.exists(grid), grid
        info = sf.info(clip)
        dur = info.frames / float(info.samplerate)
        expected = s["end_s"] - s["start_s"]
        assert abs(dur - expected) < 0.005, (s["id"], dur, expected)
