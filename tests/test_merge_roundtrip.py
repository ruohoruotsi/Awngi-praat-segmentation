"""T4: split a real annotated master into clip grids, merge back, compare.

Uses the student's actual 1203 annotation (Sound + Word tiers) as ground
truth: we graft it onto a pipeline-style master (with Utterance tier from the
real VAD segments), slice it per segment with clip_grid_for, merge all clips
back with merge_master, and verify labelled content survives the round trip.

Content that falls in the silent gaps between VAD segments is lost by design;
the comparison accounts for that.
"""

import os

import textgrids


def _labeled(intervals):
    return sorted((round(iv.xmin, 6), round(iv.xmax, 6), str(iv.text).strip())
                  for iv in intervals if str(iv.text).strip())


def _coalesce(intervals):
    out = []
    for a, b, lab in intervals:
        if out and out[-1][1] == a and out[-1][2] == lab:
            out[-1] = (out[-1][0], b, lab)
        else:
            out.append((a, b, lab))
    return out


def test_split_merge_roundtrip_on_real_annotations(seg_output, student_grid):
    from pipeline.manifest import load_manifest
    from pipeline.merge import merge_master
    from pipeline.textgrid import build_master_grid, clip_grid_for

    m = load_manifest(seg_output)
    duration = m["source"]["duration_s"]
    segs = [(s["start_s"], s["end_s"]) for s in m["segments"]]

    # ground truth: student's real annotation tiers on this exact recording
    assert abs(float(student_grid["Sound"][-1].xmax) - duration) < 0.01
    master = build_master_grid(duration, segs)
    master["Word"] = textgrids.Tier()
    for iv in student_grid["Word"]:
        master["Word"].append(textgrids.Interval(xmin=iv.xmin, xmax=iv.xmax, text=str(iv.text)))
    master["Sound"] = textgrids.Tier()
    for iv in student_grid["Sound"]:
        master["Sound"].append(textgrids.Interval(xmin=iv.xmin, xmax=iv.xmax, text=str(iv.text)))

    # split into per-clip grids (master uses short ids), then merge back
    clip_grids = []
    for i, s in enumerate(m["segments"]):
        short_id = "seg_%04d" % (i + 1)
        clip = clip_grid_for(master, short_id)
        clip_grids.append((short_id, s["start_s"], clip))

    merged = build_master_grid(duration, segs)  # fresh scaffold
    merge_master(merged, clip_grids)

    for tier in ("Sound", "Word"):
        # exact round-trip expectation: every original labelled interval,
        # clipped to the segment spans (boundary-crossing parts are trimmed
        # by the split and restored by the merge)
        exp = []
        for a, b, lab in _labeled(master[tier]):
            for sa, sb in segs:
                lo, hi = max(a, sa), min(b, sb)
                if hi > lo + 1e-9:
                    exp.append((round(lo, 6), round(hi, 6), lab))
        got = _labeled(merged[tier])
        assert _coalesce(sorted(got)) == _coalesce(sorted(exp)), "tier %s mismatch:\nmissing=%r\nextra=%r" % (
            tier, [w for w in exp if w not in got], [g for g in got if g not in exp])
