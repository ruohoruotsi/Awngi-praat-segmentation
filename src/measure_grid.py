"""Extract per-stop acoustic measures from an annotated master TextGrid.

One row per labelled interval on the Sound tier. VOT / closure come straight
from the CO/BR/VO marker midpoints; spectral features come from a short window
starting at the BR marker (configurable). Missing markers yield empty cells,
never wrong numbers.
"""

import csv
import os

import numpy as np
import soundfile as sf

from . import features


def _label_at(tier, t):
    for iv in tier:
        if iv.xmin <= t < iv.xmax:
            return str(iv.text).strip()
    return ""


def measure_grid(grid, audio, sr, window_s=0.04, cep_n=12):
    """Yield one measurement dict per labelled stop in the grid."""
    from ..textgrid import assign_markers

    sound = [iv for iv in grid["Sound"] if str(iv.text).strip()]
    per_stop, _, _ = assign_markers(grid)

    rows = []
    for stop_iv, markers in zip(sound, per_stop):
        label = str(stop_iv.text).strip()
        stop_mid = 0.5 * (stop_iv.xmin + stop_iv.xmax)

        row = {
            "stop": label,
            "t_co_s": markers.get("CO"),
            "t_br_s": markers.get("BR"),
            "t_vo_s": markers.get("VO"),
        }
        if "Utterance" in grid:
            row["segment_id"] = _label_at(grid["Utterance"], stop_mid) or None
        else:
            row["segment_id"] = None
        row["word"] = _label_at(grid["Word"], stop_mid) if "Word" in grid else None

        if "CO" in markers and "BR" in markers:
            row["closure_ms"] = (markers["BR"] - markers["CO"]) * 1000.0
        else:
            row["closure_ms"] = None
        if "BR" in markers and "VO" in markers:
            row["vot_ms"] = (markers["VO"] - markers["BR"]) * 1000.0
        else:
            row["vot_ms"] = None

        if "BR" in markers:
            win = features.window_signal(audio, sr, markers["BR"], window_s)
            moments = features.spectral_moments(win, sr)
            if moments:
                row["spec_centroid_hz"] = moments[0]
                row["spec_spread_hz"] = moments[1]
                row["spec_skewness"] = moments[2]
                row["spec_kurtosis"] = moments[3]
            else:
                row.update(spec_centroid_hz=None, spec_spread_hz=None,
                           spec_skewness=None, spec_kurtosis=None)
            burst_s = features.estimate_burst_duration(audio, sr, markers["BR"])
            row["burst_ms_est"] = burst_s * 1000.0 if burst_s else None
            cep = features.cepstrum_coeffs(win, sr, cep_n)
        else:
            row.update(spec_centroid_hz=None, spec_spread_hz=None,
                       spec_skewness=None, spec_kurtosis=None, burst_ms_est=None)
            cep = [None] * cep_n

        for i, c in enumerate(cep):
            row["c%02d" % i] = c
        rows.append(row)
    return rows


def run_measure(out_dir, csv_path, window_s=0.04, cep_n=12, audio_override=None):
    from ..manifest import load_manifest

    manifest = load_manifest(out_dir)
    if manifest is None:
        raise SystemExit("no manifest.json in %s" % out_dir)
    src = manifest["source"]["path"]
    if audio_override:
        wav_path = audio_override
    else:
        candidates = [src, os.path.join(os.path.dirname(out_dir), os.path.dirname(out_dir), src)]
        wav_path = next((c for c in candidates if os.path.exists(c)), None)
    if not wav_path or not os.path.exists(wav_path):
        raise SystemExit("audio not found: %s (pass --audio)" % src)

    from .. import textgrid as tg

    master_grid = tg.read_grid(os.path.join(out_dir, manifest["master_textgrid"]))
    audio, sr = sf.read(wav_path, dtype="float64")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    rows = measure_grid(master_grid, audio, sr, window_s=window_s, cep_n=cep_n)
    recording = os.path.splitext(os.path.basename(manifest["source"]["path"]))[0]

    fields = ["recording", "segment_id", "word", "stop",
              "t_co_s", "t_br_s", "t_vo_s", "closure_ms", "vot_ms",
              "burst_ms_est", "spec_centroid_hz", "spec_spread_hz",
              "spec_skewness", "spec_kurtosis"] + ["c%02d" % i for i in range(cep_n)] + \
             ["burst_ms_manual"]
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = {"recording": recording, "burst_ms_manual": ""}
            out.update({k: ("" if v is None else v) for k, v in row.items()})
            writer.writerow(out)
    return csv_path, len(rows)
