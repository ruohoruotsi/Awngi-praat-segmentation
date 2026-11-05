"""Merge student-annotated per-clip TextGrids back into the master grid.

For each segment in the manifest, labelled content from the Word / Sound /
Events tiers of its clip grid is offset by the segment start time and inserted
into the corresponding master tier. The Utterance tier (pipeline-owned) is
never touched. Where a clip label overlaps an existing master label, the clip
wins and the conflict is recorded in merge_report.json.
"""

import json
import os
from datetime import datetime, timezone

import textgrids

from . import textgrid as tg


def _label_at(intervals, t):
    for iv in intervals:
        if iv.xmin <= t < iv.xmax or (t == iv.xmax and str(iv.text).strip()):
            return str(iv.text)
    return ""


def merge_tier(master_intervals, incoming, eps=1e-9):
    """Merge two interval-tier contents over their combined time span.

    ``master_intervals`` / ``incoming``: lists of (xmin, xmax, label).
    Returns (merged list of (xmin, xmax, label), conflicts list).
    Clip labels win on overlap; differing non-empty labels are reported.
    """
    bounds = {0.0}
    for a, b, _ in master_intervals:
        bounds.add(a)
        bounds.add(b)
    for a, b, _ in incoming:
        bounds.add(a)
        bounds.add(b)
    bounds = sorted(bounds)
    lo, hi = bounds[0], bounds[-1]

    def label_of(intervals, mid):
        for a, b, lab in intervals:
            if a <= mid < b - eps or (b == hi and a <= mid <= b):
                return lab
        return ""

    merged = []
    conflicts = []
    for a, b in zip(bounds, bounds[1:]):
        if b - a < eps:
            continue
        mid = 0.5 * (a + b)
        m_lab = label_of(master_intervals, mid)
        i_lab = label_of(incoming, mid)
        if i_lab.strip():
            lab = i_lab
            if m_lab.strip() and m_lab.strip() != i_lab.strip():
                conflicts.append((round(a, 6), round(b, 6), m_lab, i_lab))
        else:
            lab = m_lab
        merged.append((a, b, lab))
    return _coalesce(merged), conflicts


def _coalesce(intervals):
    out = []
    for a, b, lab in intervals:
        if out and out[-1][2] == lab:
            out[-1] = (out[-1][0], b, lab)
        else:
            out.append((a, b, lab))
    return out


def merge_master(master_grid, clip_grids):
    """Merge labelled content of clip grids into master grid (in place).

    ``clip_grids``: list of (seg_id, start_s, grid). Returns conflict report.
    """
    report = {
        "merged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "segments_merged": 0,
        "conflicts": [],
    }
    for name in ("Word", "Sound", "Events"):
        if name not in master_grid:
            continue
        master_intervals = [(iv.xmin, iv.xmax, str(iv.text)) for iv in master_grid[name]]
        for seg_id, start_s, grid in clip_grids:
            if name not in grid or not len(grid[name]):
                continue
            incoming = [
                (iv.xmin + start_s, iv.xmax + start_s, str(iv.text))
                for iv in grid[name]
                if str(iv.text).strip()
            ]
            if not incoming:
                continue
            master_intervals, conflicts = merge_tier(master_intervals, incoming)
            report["segments_merged"] += 1
            for a, b, m_lab, i_lab in conflicts:
                report["conflicts"].append(
                    {"segment": seg_id, "tier": name, "t_start": a, "t_end": b,
                     "master_label": m_lab, "clip_label": i_lab, "resolution": "clip wins"}
                )
        tier = master_grid[name]
        del tier[:]
        for a, b, lab in master_intervals:
            tier.append(textgrids.Interval(xmin=a, xmax=b, text=lab))
    return report


def run_merge(out_dir):
    """Merge all clip grids in an output dir into its master grid."""
    from .manifest import load_manifest

    manifest = load_manifest(out_dir)
    if manifest is None:
        raise SystemExit("no manifest.json in %s" % out_dir)
    master_path = os.path.join(out_dir, manifest["master_textgrid"])
    master_grid = tg.read_grid(master_path)
    clip_grids = []
    for seg in manifest["segments"]:
        grid_path = os.path.join(out_dir, seg["textgrid"])
        if os.path.exists(grid_path):
            clip_grids.append((seg["id"], seg["start_s"], tg.read_grid(grid_path)))
    report = merge_master(master_grid, clip_grids)
    tg.write_grid(master_grid, master_path)
    report_path = os.path.join(out_dir, "merge_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    return report
