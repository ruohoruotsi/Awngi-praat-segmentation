"""Annotation consistency lint.

Checks that each labelled stop on the Sound tier carries exactly one CO, one
BR and one VO marker on the Events tier, in a sane order, with plausible
durations. Gives the advisor-facing QA gate before measurement: consistent
boundaries are the whole point of the manual-annotation requirement.

Marker times use the midpoint of each marker interval (markers should be
short boxes; wide ones are flagged).
"""

MARKERS = ("CO", "BR", "VO")
MAX_MARKER_MS = 100.0   # a marker box wider than this is probably mis-drawn
WARN_VOT_MS = 150.0     # |VOT| beyond this is unusual for stops -> warn
WARN_CLOSURE_MS = 300.0


def _mid(iv):
    return 0.5 * (iv.xmin + iv.xmax)


def validate_grid(grid):
    """Return a list of issue dicts: {severity, tier, t, stop, message}."""
    issues = []

    def add(severity, msg, t=None, stop=None, tier=""):
        issues.append({"severity": severity, "tier": tier, "t": t, "stop": stop, "message": msg})

    if "Sound" not in grid or "Events" not in grid:
        return [{"severity": "error", "tier": "", "t": None, "stop": None,
                 "message": "grid must have Sound and Events tiers"}]

    from .textgrid import assign_markers

    sound = [iv for iv in grid["Sound"] if str(iv.text).strip()]
    events = [iv for iv in grid["Events"] if str(iv.text).strip()]

    # marker hygiene: labels must be known, boxes must be short
    for iv in events:
        lab = str(iv.text).strip()
        if lab not in MARKERS:
            add("error", "unknown Events label %r (expected CO/BR/VO)" % lab, _mid(iv), tier="Events")
        width_ms = (iv.xmax - iv.xmin) * 1000.0
        if width_ms > MAX_MARKER_MS:
            add("warning", "%s marker is %.0f ms wide (should be a short box)" % (lab, width_ms),
                _mid(iv), tier="Events")

    per_stop, unassigned, dups = assign_markers(grid)
    for t, lab in unassigned:
        add("warning", "%s marker at %.3fs is not near any labelled stop" % (lab, t), t, tier="Events")
    for t, lab, i in dups:
        add("error", "duplicate %s marker for stop %r" % (lab, str(sound[i].text).strip()),
            t, str(sound[i].text).strip(), "Events")

    for stop_iv, mids in zip(sound, per_stop):
        label = str(stop_iv.text).strip()
        for missing in MARKERS:
            if missing not in mids:
                add("error", "stop %r has no %s marker" % (label, missing), None, label, "Events")
        if len(mids) < 2:
            continue

        t_co, t_br = mids.get("CO"), mids.get("BR")
        t_vo = mids.get("VO")
        if t_co is not None and t_br is not None and t_co >= t_br:
            add("error", "stop %r: closure onset (CO) must precede burst (BR)" % label, t_br, label, "Events")
        if t_co is not None and t_br is not None:
            closure_ms = (t_br - t_co) * 1000.0
            if closure_ms > WARN_CLOSURE_MS:
                add("warning", "stop %r: closure duration %.0f ms looks long" % (label, closure_ms), t_co, label)
        if t_vo is not None and t_br is not None:
            vot_ms = (t_vo - t_br) * 1000.0
            if abs(vot_ms) > WARN_VOT_MS:
                add("warning", "stop %r: VOT %.0f ms looks unusual" % (label, vot_ms), t_vo, label)

    # soft check: stops should sit inside a labelled Word interval
    words = [iv for iv in grid["Word"]] if "Word" in grid else []
    if any(str(iv.text).strip() for iv in words):
        for stop_iv in sound:
            mid = _mid(stop_iv)
            if not any(iv.xmin <= mid < iv.xmax and str(iv.text).strip() for iv in words):
                add("warning", "stop %r is outside any labelled Word interval" % str(stop_iv.text).strip(),
                    mid, str(stop_iv.text).strip(), "Word")

    return issues


def format_issues(issues):
    lines = []
    for iss in issues:
        t = ("t=%.3fs" % iss["t"]) if iss["t"] is not None else ""
        stop = ("stop=%r" % iss["stop"]) if iss["stop"] else ""
        lines.append("%-7s %-8s %-10s %s  %s" % (iss["severity"], iss["tier"], t, stop, iss["message"]))
    return "\n".join(lines)
