"""Praat TextGrid generation for the segmentation pipeline.

We use the pure-Python ``praat-textgrids`` library (imported as ``textgrids``)
so no Praat installation is required to *produce* grids. It also reads every
Praat flavour (long/short text and binary, UTF-8 or UTF-16), which we rely on
for the merge / validate / measure steps that consume student-edited grids.

Tier layout (coarse -> fine):
    Utterance  IntervalTier  segment ids, pre-filled by the pipeline
    Word       IntervalTier  word-level transcription (empty scaffold)
    Sound      IntervalTier  stop labels, one per stop (empty scaffold)
    Events     IntervalTier  CO / BR / VO markers as short labelled intervals

Events is an IntervalTier rather than a PointTier on purpose: praat-textgrids
cannot serialise point tiers, and short marker boxes are just as easy to place
in Praat. A marker's time is taken from the *midpoint* of its interval.
"""

import textgrids

TIER_ORDER = ["Utterance", "Word", "Sound", "Events"]
EVENT_LABELS = ("CO", "BR", "VO")


def _interval_tier(duration, spans):
    """Build a contiguous IntervalTier over [0, duration].

    ``spans`` is an iterable of (xmin, xmax, label), sorted and non-overlapping.
    Gaps between spans are filled with empty labels so the tier always covers
    the whole time axis exactly, as Praat requires.
    """
    tier = textgrids.Tier()
    cursor = 0.0
    for xmin, xmax, label in sorted(spans, key=lambda s: s[0]):
        if xmin > cursor:
            _append(tier, cursor, min(xmin, duration), "")
        lo = max(cursor, xmin)
        hi = min(duration, xmax)
        if hi > lo:
            _append(tier, lo, hi, label)
        cursor = max(cursor, hi)
    if cursor < duration:
        _append(tier, cursor, duration, "")
    return tier


def _append(tier, xmin, xmax, label):
    if xmax > xmin:
        tier.append(textgrids.Interval(xmin=xmin, xmax=xmax, text=label))


def build_master_grid(duration, segments):
    """Master TextGrid for a whole recording.

    ``segments`` is a list of (start_s, end_s). The Utterance tier is labelled
    with stable ids (seg_0001 ...); the other tiers are empty scaffolds.
    """
    utterance_spans = []
    for i, (start, end) in enumerate(segments):
        utterance_spans.append((start, end, "seg_%04d" % (i + 1)))
    grid = textgrids.TextGrid()
    grid["Utterance"] = _interval_tier(duration, utterance_spans)
    for name in TIER_ORDER[1:]:
        grid[name] = _interval_tier(duration, [])
    return grid


def build_clip_grid(clip_duration, seg_id):
    """Per-utterance TextGrid rebased to [0, clip_duration]."""
    grid = textgrids.TextGrid()
    grid["Utterance"] = _interval_tier(clip_duration, [(0.0, clip_duration, seg_id)])
    for name in TIER_ORDER[1:]:
        grid[name] = _interval_tier(clip_duration, [])
    return grid


def write_grid(grid, path):
    """Write a TextGrid to ``path`` in long-text format (Praat-readable).

    praat-textgrids keeps the header xmin/xmax as plain object attributes;
    grids built in memory default them to 0.0, which Praat would reject.
    Derive them from the tier contents before writing.
    """
    if len(grid):
        first = next(iter(grid.values()))
        grid.xmin = float(first[0].xmin)
        grid.xmax = float(first[-1].xmax)
    grid.write(path)


def read_grid(path):
    """Read any Praat TextGrid flavour from ``path``."""
    return textgrids.TextGrid(path)


def segment_ids(grid):
    """Return [(start, end, id)] for the labelled Utterance tier of a grid."""
    out = []
    if "Utterance" in grid:
        for iv in grid["Utterance"]:
            label = str(iv.text).strip()
            if label:
                out.append((iv.xmin, iv.xmax, label))
    return out


def clip_grid_for(master_grid, seg_id):
    """Rebase a slice of an annotated master grid to a standalone clip grid.

    Used by the merge step to split a student-annotated master back into clips,
    and for round-trip testing.
    """
    spans = segment_ids(master_grid)
    match = [s for s in spans if s[2] == seg_id]
    if not match:
        raise KeyError("segment id %r not found in grid" % seg_id)
    start, end = match[0][0], match[0][1]
    dur = end - start
    out = textgrids.TextGrid()
    for name in TIER_ORDER:
        if name == "Utterance":
            out[name] = _interval_tier(dur, [(0.0, dur, seg_id)])
        elif name in master_grid:
            src = master_grid[name]
            rel_spans = []
            for iv in src:
                lo = max(iv.xmin, start) - start
                hi = min(iv.xmax, end) - start
                if hi > lo:
                    rel_spans.append((lo, hi, str(iv.text)))
            out[name] = _interval_tier(dur, rel_spans)
        else:
            out[name] = _interval_tier(dur, [])
    return out


def grid_duration(grid):
    """Return the xmax of the first tier (all tiers share it)."""
    for name in TIER_ORDER:
        if name in grid and len(grid[name]):
            return float(grid[name][-1].xmax)
    raise ValueError("grid has no intervals")


def assign_markers(grid, before_s=0.15, after_s=0.35):
    """Assign CO/BR/VO markers (Events tier) to labelled Sound stops.

    Student-drawn stop boxes are narrow (closure+burst), but voicing onset
    runs into the following vowel - so a marker belongs to a stop if its
    midpoint falls in [stop.xmin - before_s, stop.xmax + after_s]. If several
    stops claim a marker, the nearest wins.

    Returns (per_stop, unassigned, dups): per_stop is a list parallel to the
    labelled stops of {label: midpoint}; unassigned is [(t, label)] and
    dups is [(t, label, stop_index)].
    """
    sound = [iv for iv in grid["Sound"] if str(iv.text).strip()]
    per_stop = [{} for _ in sound]
    unassigned = []
    dups = []
    for iv in grid["Events"]:
        lab = str(iv.text).strip()
        if lab not in EVENT_LABELS:
            continue
        t = 0.5 * (iv.xmin + iv.xmax)
        candidates = [i for i, s in enumerate(sound)
                      if s.xmin - before_s <= t <= s.xmax + after_s]
        if not candidates:
            unassigned.append((t, lab))
            continue
        if len(candidates) > 1:

            def dist(i):
                s = sound[i]
                return 0.0 if s.xmin <= t <= s.xmax else min(abs(t - s.xmin), abs(t - s.xmax))

            candidates = [min(candidates, key=dist)]
        i = candidates[0]
        if lab in per_stop[i]:
            dups.append((t, lab, i))
        per_stop[i][lab] = t
    return per_stop, unassigned, dups
