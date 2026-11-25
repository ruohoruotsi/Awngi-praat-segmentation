# Burst Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Analytic burst detector for word-initial Awngi stops: `src/detect_bursts.py` that proposes release-burst boundaries (onset/offset/confidence) as CSV + a Praat proposal TextGrid, validated against the annotated `burst` tiers in `audio/`.

**Architecture:** Super-flux-style short-frame spectral flux (5 ms Hann frames, ~2.3 ms hop, positive magnitude difference with high-pass frequency weighting), two-stage adaptive threshold (global median+k·MAD, then local ±0.5 s baseline per peak), peak picking with min-gap and duration veto, rising-edge onset / last-active-frame offset. Pure numpy/scipy.

**Tech Stack:** Python 3.10, numpy, scipy, soundfile, praat-textgrids, pytest. No new dependencies (no madmom).

**Spec:** `docs/superpowers/specs/2026-11-24-burst-detection-design.md` (data survey: `docs/GROUNDTRUTH.md`)

## Global Constraints

- Audio is never resampled or normalised: 44.1 kHz mono PCM16 native rate.
- Dependencies: numpy, scipy, soundfile, praat-textgrids, pytest only.
- TDD per AGENTS.md: write the test first, run it ONE AT A TIME with
  `segmentation_venv/bin/python -m pytest tests/<file>::<test> -v`, show each
  run's output, then minimal implementation.
- Do NOT commit (AGENTS.md): all changes stay in the working tree; the user commits.
- Stock defaults first: the pilot (Task 6) runs with un-tuned defaults; any
  calibration happens only after the pilot report is shown to the user.
- Output grids must never overwrite an existing tier; M.'s layout conventions
  per docs/GROUNDTRUTH.md.

## Review Focus

1. Real recordings have mic noise/hum, not digital silence → steady hum must not
   yield burst candidates (pinned: Task 6, real-file runs incl. 1202/1203).
2. A stop token with absent/weak release → no candidate, listed in the pilot
   miss list, no crash (pinned: Task 6, miss list in report).
3. Multi-channel WAV → averaged to mono, no shape crash (pinned: Task 5).
4. Burst at the very start/end of a file → frame-boundary safe, still detected
   (pinned: Task 5).
5. Input grid already containing a `burst` tier (all pilot files do) → proposals
   go to `burst_auto`; the GT `burst` tier comes back byte-identical (pinned:
   Task 5).

---

### Task 1: Housekeeping — green baseline on the new layout

**Files:**
- Create: `src/__init__.py` (empty)
- Modify: `src/measure_grid.py:27` (import fix)
- Modify: `tests/conftest.py`, `tests/test_measure.py`, `tests/test_validate.py` (stale `pipeline.*` imports)
- Modify: `requirements.txt`, `README.md`, `.gitignore`

**Interfaces:**
- Produces: working `src` package importable as `src.<module>`; full existing
  suite green. Later tasks import `src.textgrid` (`read_grid`, `_interval_tier`).

- [ ] **Step 1: Environment**

```bash
python3.10 -m venv segmentation_venv
segmentation_venv/bin/pip install -r requirements.txt
```

- [ ] **Step 2: Make the edits**

- `src/__init__.py`: empty file.
- `src/measure_grid.py:27`: `from ..textgrid import assign_markers` → `from .textgrid import assign_markers`. (Leave `run_measure`'s call-time `..manifest` import alone — follow-up.)
- `tests/conftest.py`: delete the `seg_output` fixture (imports deleted `pipeline.__main__`); `student_grid`: `from pipeline.textgrid import read_grid` → `from src.textgrid import read_grid`.
- `tests/test_measure.py`: `from pipeline.measure.extract import measure_grid` → `from src.measure_grid import measure_grid`; `from pipeline.textgrid import _interval_tier` → `from src.textgrid import _interval_tier`.
- `tests/test_validate.py`: `from pipeline.textgrid import _interval_tier` → `from src.textgrid import _interval_tier`; `from pipeline.validate import validate_grid` → `from src.validate import validate_grid`.
- `requirements.txt`: remove `runez`, `torchcodec`, `silero-vad` lines. Result: `praat-textgrids`, `soundfile`, `scipy`, `numpy`, and dev `pytest`.
- `README.md` quickstart: replace the `python -m src.auto_annotate.py ...` line with `python -m src.detect_bursts audio/1203_spm37_intervocalic.WAV --out out/` (comment: "burst detection -> candidates CSV + proposal TextGrid"). Update the repo-layout block: `detect_bursts.py` = "burst detector (spectral flux, adaptive threshold)"; drop the stale `auto_annotate` line if present.
- `.gitignore`: add `segmentation_venv/`.

- [ ] **Step 3: Run the suite**

Run: `segmentation_venv/bin/python -m pytest tests/ -q`
Expected: all pass (test_measure: 5, test_validate: 6).

### Task 2: `burst_flux` — the flux feature

**Files:**
- Create: `src/detect_bursts.py`
- Test: `tests/test_detect_bursts.py`

**Interfaces:**
- Produces: `burst_flux(x, sr, frame_ms=5.0, hop_ms=2.3, fc0=500.0, fc1=1500.0) -> (times: np.ndarray, flux: np.ndarray)` — `x` mono float64; `times` = frame-center times in seconds, `len(times) == len(flux)`; `flux[t] = Σ_b max(0, |S[t+1,b]| − |S[t,b]|) · w(f)` with Hann frames and `w(f)` = 0 below `fc0`, linear ramp to 1 at `fc1` (1 above).
- Consumes: nothing (numpy only).

- [ ] **Step 1: Write the failing tests** (`tests/test_detect_bursts.py`)

```python
import numpy as np
import pytest

pytestmark = pytest.mark.filterwarnings("ignore")

SR = 44100

def make_tone(sr, f0, t_start, duration=2.0, amp=0.5):
    t = np.arange(int(sr * duration)) / sr
    x = np.zeros_like(t)
    m = t >= t_start
    x[m] = amp * np.sin(2 * np.pi * f0 * t[m])
    return x

def test_flux_silence_is_zero():
    from src.detect_bursts import burst_flux
    times, flux = burst_flux(np.zeros(44100 * 2), SR)
    assert len(times) == len(flux) > 100
    assert flux.max() == 0.0

def test_flux_spikes_at_tone_onset_then_decays():
    from src.detect_bursts import burst_flux
    x = make_tone(SR, 2000.0, t_start=0.5)
    times, flux = burst_flux(x, SR)
    peak_i = int(np.argmax(flux))
    assert 0.48 < times[peak_i] < 0.56
    assert flux[(times > 0.7) & (times < 2.0)].max() < 1e-3 * flux[peak_i]

def test_flux_highpass_suppresses_lowband():
    from src.detect_bursts import burst_flux
    x = make_tone(SR, 200.0, t_start=0.5)   # below fc0 -> fully unweighted
    _, flux = burst_flux(x, SR)
    # Hann leakage into weighted bins is tiny; a real burst's flux is orders higher
    assert flux.max() < 1e-2, flux.max()
```

- [ ] **Step 2: Run tests, verify they fail** (one at a time)

Run: `segmentation_venv/bin/python -m pytest tests/test_detect_bursts.py::test_flux_silence_is_zero -v`
Expected: FAIL with `ModuleNotFoundError` / `cannot import name 'burst_flux'`. Run the other two the same way.

- [ ] **Step 3: Implement `burst_flux` in `src/detect_bursts.py`**

Module docstring: purpose (analytic burst detector, super-flux-style, no SSL),
the signal chain, and current default values. Implementation: frame indices by
hop; per-frame Hann-windowed `rfft` magnitudes into an array `S`; per-bin
weights from `rfftfreq`; `flux[t] = (np.maximum(0, S[t+1] - S[t]) * w).sum()`
for `t` in `0..n-2` (flux array is one shorter than S — build `times` from the
frames that HAVE a successor, i.e. centers of frames 0..n-2).

- [ ] **Step 4: Run tests, verify they pass** (one at a time, show output)

Run: `segmentation_venv/bin/python -m pytest tests/test_detect_bursts.py -v`
Expected: 3 passed.

### Task 3: `detect_bursts` — core chain (silence, noise pulse, tone)

**Files:**
- Modify: `src/detect_bursts.py`
- Test: `tests/test_detect_bursts.py`

**Interfaces:**
- Produces: `Burst` dataclass with fields `onset_s: float, offset_s: float, duration_ms: float, score: float, peak_flux: float, confidence: float`
  (`duration_ms = (offset_s − onset_s) * 1000`; `score` = local prominence in MAD units; `peak_flux` = raw flux at the peak frame).
  `detect_bursts(x, sr, frame_ms=5.0, hop_ms=2.3, fc0=500.0, fc1=1500.0, k=5.0, min_gap_s=0.1, min_burst_ms=3.0, max_burst_ms=150.0) -> list[Burst]` — sorted by onset.
- Consumes: `burst_flux` (Task 2).

- [ ] **Step 1: Write the failing tests**

```python
def make_pulse(x, t0, dur=0.030, amp=0.5, seed=0):
    i0, i1 = int(t0 * SR), int((t0 + dur) * SR)
    x[i0:i1] = amp * np.random.default_rng(seed).normal(0, 1, i1 - i0)
    return x

def test_silence_no_detections():
    from src.detect_bursts import detect_bursts
    assert detect_bursts(np.zeros(SR * 2), SR) == []

def test_noise_pulse_detected():
    from src.detect_bursts import detect_bursts
    x = np.zeros(SR * 2)
    make_pulse(x, 1.000, dur=0.030)
    b = detect_bursts(x, SR)
    assert len(b) == 1, b
    assert abs(b[0].onset_s - 1.000) <= 0.005, b[0].onset_s
    assert abs(b[0].offset_s - 1.030) <= 0.010, b[0].offset_s
    assert 0.0 < b[0].confidence <= 1.0

def test_steady_tone_no_detections():
    from src.detect_bursts import detect_bursts
    assert detect_bursts(make_tone(SR, 2000.0, t_start=0.0, duration=2.0), SR) == []
```

- [ ] **Step 2: Run each, verify they fail** (one at a time)

Run: `segmentation_venv/bin/python -m pytest tests/test_detect_bursts.py::test_silence_no_detections -v`
Expected: FAIL (`cannot import name 'detect_bursts'`). Same for the other two.

- [ ] **Step 3: Implement `detect_bursts` in `src/detect_bursts.py`**

Chain (spec §"Design: module"):
1. `times, flux = burst_flux(...)`.
2. Coarse threshold `thr_g = median(flux) + k * mad(flux)` (MAD = median of
   |flux − median|; if MAD == 0 use a tiny floor). Candidate peaks = local
   maxima above `thr_g`.
3. Enforce `min_gap_s`: among overlapping candidates keep the highest flux.
4. Per surviving peak: local window = flux within ±0.5 s of the peak;
   `base = median(local)`, `mad_l = median(|local − base|)` (floor as above);
   active region = contiguous frames above `base + k * mad_l` containing the
   peak; veto if region length < `min_burst_ms` or > `max_burst_ms` (in time).
5. `onset_s` = time just before the active region's first frame (rising edge:
   the last frame ≤ `base + 1*mad_l` before it, + one hop); `offset_s` = center
   of the last active frame (2-frame gap tolerance inside the region).
6. `score = (peak_flux − base) / mad_l`; `peak_flux` = flux at peak frame;
   `confidence = score / (score + 10.0)` clipped to [0, 1]
   (soft 10-MAD saturation — one-line explainable).
7. Sort by onset, return.

- [ ] **Step 4: Run tests, verify they pass** (one at a time, show output)

Run: `segmentation_venv/bin/python -m pytest tests/test_detect_bursts.py -v`
Expected: 6 passed.

### Task 4: Robustness — labial burst, vowel ramp, two pulses, confidence

**Files:**
- Modify: `src/detect_bursts.py` (only if red tests require chain tweaks)
- Test: `tests/test_detect_bursts.py`

**Interfaces:**
- Consumes: `detect_bursts` (Task 3) — no signature change.

- [ ] **Step 1: Write the failing tests**

```python
def make_band_noise(sr, t0, dur, lo, hi, amp=0.2, seed=1):
    n = int(dur * sr)
    t = np.arange(n) / sr
    x = amp * np.random.default_rng(seed).normal(0, 1, n)
    # crude band-limit with a scipy butter filter
    from scipy.signal import butter, sosfilt
    nyq = sr / 2
    sos = butter(4, [lo / nyq, hi / nyq], btype="band")
    y = np.zeros(sr * 2)
    i0 = int(t0 * sr)
    y[i0:i0 + n] = sosfilt(sos, x) * np.hanning(n)
    return y

def test_weak_labial_burst_detected():
    from src.detect_bursts import detect_bursts
    x = make_band_noise(SR, 1.2, 0.025, 200, 3000, amp=0.2)
    b = detect_bursts(x, SR)
    assert len(b) == 1, b
    assert abs(b[0].onset_s - 1.2) <= 0.008, b[0].onset_s

def test_vowel_onset_ramp_not_detected():
    from src.detect_bursts import detect_bursts
    # silence, then a 200 ms rising formant-like sweep (broad, slow -> vetoed)
    dur = 2.0
    t = np.arange(int(SR * dur)) / SR
    x = np.zeros_like(t)
    m = t >= 0.5
    f = 300 + (700 - 300) * (t[m] - 0.5) / 0.2
    env = np.clip((t[m] - 0.5) / 0.2, 0, 1)
    x[m] = 0.4 * env * np.sin(2 * np.pi * np.cumsum(f) / SR)
    assert detect_bursts(x, SR) == []

def test_two_pulses_both_detected():
    from src.detect_bursts import detect_bursts
    x = np.zeros(SR * 2)
    make_pulse(x, 1.000, dur=0.030, seed=0)
    make_pulse(x, 1.500, dur=0.020, seed=2)
    b = detect_bursts(x, SR)
    assert len(b) == 2, b
    assert b[0].onset_s < b[1].onset_s
    assert abs(b[0].onset_s - 1.0) <= 0.005 and abs(b[1].onset_s - 1.5) <= 0.005

def test_confidence_ordering():
    from src.detect_bursts import detect_bursts
    x = np.zeros(SR * 2)
    make_pulse(x, 1.000, dur=0.030, amp=0.5, seed=0)   # strong
    make_pulse(x, 1.500, dur=0.030, amp=0.15, seed=2)  # weak
    b = detect_bursts(x, SR)
    assert len(b) == 2, b
    assert b[0].confidence > b[1].confidence, (b[0].confidence, b[1].confidence)
```

- [ ] **Step 2: Run each, verify failures where expected** (one at a time)

Some may already pass from Task 3 — that's fine, record which. Any FAIL is a
red test to fix in Step 3.

- [ ] **Step 3: Minimal fixes in `src/detect_bursts.py`**

Likely levers, in order: widen the local baseline window, adjust the 2-frame
gap tolerance, raise/lower the duration-veto interaction with the Hann edge of
`make_band_noise`. Do NOT change defaults that the spec pins (fc0=500, k=5,
gaps, 3–150 ms veto) to make a test pass — if a pinned default is genuinely
wrong for a synthetic, revisit the test's realism instead and note it.

- [ ] **Step 4: Run the whole synthetic file**

Run: `segmentation_venv/bin/python -m pytest tests/test_detect_bursts.py -v`
Expected: 10 passed.

### Task 5: Outputs — CSV, proposal TextGrid, CLI

**Files:**
- Modify: `src/detect_bursts.py`
- Test: `tests/test_detect_bursts.py`

**Interfaces:**
- Produces:
  - `load_audio(path) -> (x: np.ndarray[float64], sr: int)` — soundfile, mono mean if multichannel.
  - `write_proposed_grid(in_grid_path, out_path, bursts, duration)` — copies every input tier as-is; adds ONE new IntervalTier with a box [onset, max(offset, onset+5 ms)] per burst; label = `<consonant-label>_br` when the input has a `consonant` tier and the onset sits inside or within 100 ms of a labelled consonant box, else `f"{confidence:.2f}"`; tier name = `burst_auto` if the input already has a `burst` tier, else `burst`; inserted just before `VOT` when present, else appended. Never overwrites an existing tier.
  - `main(argv: list[str]) -> int` — argparse: `wav` (positional), `--out` (required dir), `--fc0`, `--fc1`, `--k`, `--min-gap`, `--min-burst-ms`, `--max-burst-ms`, `--no-grid`. Writes `<out>/<stem>_bursts.csv` (columns: `t_onset_s,t_offset_s,duration_ms,score,peak_flux,confidence`) always; writes the proposal grid only when a co-located `<wav-stem>.TextGrid` exists and `--no-grid` is absent; returns 0.
- Consumes: `detect_bursts` (Task 3/4), `src.textgrid.read_grid` + `write_grid`.

- [ ] **Step 1: Write the failing tests**

```python
import os

def make_gt_grid(path, dur=2.0):
    import textgrids
    from src.textgrid import _interval_tier
    g = textgrids.TextGrid()
    g["word"] = _interval_tier(dur, [(0.9, 1.4, "kari")])
    g["consonant"] = _interval_tier(dur, [(0.95, 1.04, "k1")])
    g["vowel"] = _interval_tier(dur, [(1.04, 1.30, "k_a1")])
    g["burst"] = _interval_tier(dur, [(1.000, 1.006, "k1_br")])
    g["VOT"] = _interval_tier(dur, [])
    from src.textgrid import write_grid
    write_grid(g, path)
    return g

def test_cli_writes_csv_and_proposed_grid(tmp_path):
    from src.detect_bursts import main, load_audio
    wav = str(tmp_path / "w.WAV")
    import soundfile as sf
    x = np.zeros(SR * 2); make_pulse(x, 1.000, dur=0.030, seed=0)
    sf.write(wav, x, SR)
    make_gt_grid(str(tmp_path / "w.TextGrid"))
    rc = main([wav, "--out", str(tmp_path / "out")])
    assert rc == 0
    csv_p = tmp_path / "out" / "w_bursts.csv"
    grid_p = tmp_path / "out" / "w_proposed.TextGrid"
    assert csv_p.exists() and grid_p.exists()
    import csv as _csv
    rows = list(_csv.DictReader(open(csv_p)))
    assert len(rows) >= 1
    assert abs(float(rows[0]["t_onset_s"]) - 1.0) <= 0.005
    from src.textgrid import read_grid
    g = read_grid(str(grid_p))
    assert "burst" in g and "burst_auto" in g
    gt = [iv for iv in g["burst"] if str(iv.text).strip()]
    assert len(gt) == 1 and gt[0].xmin == 1.000   # GT tier untouched
    auto = [iv for iv in g["burst_auto"] if str(iv.text).strip()]
    assert len(auto) == 1
    assert str(auto[0].text) == "k1_br"
    assert abs(auto[0].xmin - 1.0) <= 0.008

def test_cli_no_grid_csv_only(tmp_path):
    from src.detect_bursts import main
    import soundfile as sf
    wav = str(tmp_path / "n.WAV")
    x = np.zeros(SR * 2); make_pulse(x, 1.0, dur=0.030, seed=0)
    sf.write(wav, x, SR)
    rc = main([wav, "--out", str(tmp_path / "out")])
    assert rc == 0
    assert (tmp_path / "out" / "n_bursts.csv").exists()
    assert not (tmp_path / "out" / "n_proposed.TextGrid").exists()

def test_cli_no_grid_flag(tmp_path):
    from src.detect_bursts import main
    import soundfile as sf
    wav = str(tmp_path / "g.WAV")
    x = np.zeros(SR * 2); make_pulse(x, 1.0, dur=0.030, seed=0)
    sf.write(wav, x, SR)
    make_gt_grid(str(tmp_path / "g.TextGrid"))
    rc = main([wav, "--out", str(tmp_path / "out"), "--no-grid"])
    assert rc == 0
    assert not (tmp_path / "out" / "g_proposed.TextGrid").exists()

def test_load_audio_stereo(tmp_path):
    from src.detect_bursts import load_audio, detect_bursts
    import soundfile as sf
    x = np.zeros(SR * 2); make_pulse(x, 1.0, dur=0.030, seed=0)
    stereo = np.stack([x, x * 0.5], axis=1)
    sf.write(str(tmp_path / "s.WAV"), stereo, SR)
    a, sr = load_audio(str(tmp_path / "s.WAV"))
    assert a.ndim == 1 and sr == SR
    b = detect_bursts(a, sr)
    assert len(b) == 1 and abs(b[0].onset_s - 1.0) <= 0.005

def test_pulses_at_file_edges():
    from src.detect_bursts import detect_bursts
    x = np.zeros(SR * 2)
    make_pulse(x, 0.005, dur=0.030, seed=0)
    make_pulse(x, 1.965, dur=0.030, seed=3)
    b = detect_bursts(x, SR)
    assert len(b) == 2, b
    assert b[0].onset_s <= 0.012 and b[1].offset_s >= 1.990
```

- [ ] **Step 2: Run each, verify they fail** (one at a time)

Expected: FAIL (`cannot import name 'main'` / 'load_audio').

- [ ] **Step 3: Implement `load_audio`, `write_proposed_grid`, `main`**

- `load_audio`: `sf.read(path, dtype="float64")`; if `ndim > 1` mean over channels.
- `write_proposed_grid`: `read_grid`; build the new tier with `src.textgrid._interval_tier` (gaps auto-filled); tier insertion order via dict re-insertion (praat-textgrids tiers keep insertion order); labels per the rule above; write with `src.textgrid.write_grid` (fixes xmin/xmax).
- `main`: argparse; `os.makedirs(out, exist_ok=True)`; co-located grid =
  `wav` path with `.WAV`→`.TextGrid` (case-insensitive match); CSV via the `csv`
  module; print a one-line summary (n candidates, grid written or not).
- `if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))`

- [ ] **Step 4: Run the whole synthetic file + full suite**

Run: `segmentation_venv/bin/python -m pytest tests/ -q`
Expected: all pass.

### Task 6: Pilot on the real recordings — stock defaults, report first

**Files:**
- Create: `tests/test_bursts_pilot.py`
- (No changes to `src/detect_bursts.py` in this task — calibration only happens
  after the report is reviewed with the user.)

**Interfaces:**
- Consumes: `detect_bursts`, `load_audio`, `main` (Task 3–5); `src.textgrid.read_grid`.
- GT source: `burst` tier of `audio/initial stops/1011_spf3_word-initial_24.TextGrid`
  (30 boxes) and `audio/intervocalic stops/1114_spm32_intervocalic-19.TextGrid` (2 boxes).

- [ ] **Step 1: Write the pilot test**

```python
"""Pilot: stock-default detector vs M.'s burst tiers. Report first, tune later."""
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

F_1011 = ("audio/initial stops/1011_spf3_word-initial_24", "word")
F_1114 = ("audio/intervocalic stops/1114_spm32_intervocalic-19", "word")
UNANNOTATED = ("audio/1202_spm37_word-initial", None)
F_1203 = ("audio/1203_spm37_intervocalic", None)

def gt_bursts(rel_path, tier="burst"):
    from src.textgrid import read_grid
    g = read_grid(os.path.join(REPO, rel_path + ".TextGrid"))
    return [(iv.xmin, iv.xmax, str(iv.text).strip())
            for iv in g[tier] if str(iv.text).strip()]

def annotated_span(rel_path, margin=1.0):
    from src.textgrid import read_grid
    g = read_grid(os.path.join(REPO, rel_path + ".TextGrid"))
    words = [iv for iv in g["word"] if str(iv.text).strip()]
    return (words[0].xmin - margin, words[-1].xmax + margin)

def match(cands, gts, tol_s=0.010):
    """Greedy 1:1 by nearest onset. TP iff onset in [gt.xmin-tol, gt.xmax+tol]."""
    hits, misses = [], []
    used = set()
    for c in sorted(cands, key=lambda c: c.onset_s):
        best = None
        for j, (a, b, lab) in enumerate(gts):
            if j in used:
                continue
            if a - tol_s <= c.onset_s <= b + tol_s:
                d = min(abs(c.onset_s - a), abs(c.onset_s - b))
                if best is None or d < best[1]:
                    best = (j, d)
        if best:
            used.add(best[0])
            hits.append((c, gts[best[0]]))
    for j, (a, b, lab) in enumerate(gts):
        if j not in used:
            misses.append((lab, a, b))
    return hits, misses

def pilot_report(name, hits, misses, cands, gts, span):
    import numpy as np
    in_span = [c for c in cands if span[0] <= c.onset_s <= span[1]]
    fas = [c for c in in_span
           if all(c.onset_s < a - 0.05 or c.onset_s > b + 0.05 for a, b, _ in gts)]
    onset_err = [(c.onset_s - min(a, b)) * 1000 for c, (a, b, _) in hits]
    offset_err = [(c.offset_s - max(a, b)) * 1000 for c, (a, b, _) in hits]
    def ms(v):
        v = np.array(v)
        return f"mean={v.mean():+.1f} median={np.median(v):+.1f} max|.|={np.abs(v).max():.1f}" if len(v) else "n/a"
    print(f"--- pilot: {name}")
    print(f"  GT boxes: {len(gts)}   candidates: {len(in_span)} in span / {len(cands)} whole file")
    print(f"  hits: {len(hits)}/{len(gts)} ({100*len(hits)/max(1,len(gts)):.0f}%)")
    print(f"  onset err (ms, vs box start): {ms(onset_err)}")
    print(f"  offset err (ms, vs box end):  {ms(offset_err)}")
    print(f"  false alarms in span: {len(fas)}" + (f" -> {[round(c.onset_s,3) for c in fas][:10]}" if fas else ""))
    print(f"  missed GT: {[lab for _, _, lab in misses] or 'none'}")

```python
def test_pilot_1011_word_initial():
    from src.detect_bursts import detect_bursts, load_audio
    rel = F_1011[0]
    x, sr = load_audio(os.path.join(REPO, rel + ".WAV"))
    gts = gt_bursts(rel)
    span = annotated_span(rel)
    cands = detect_bursts(x, sr)
    hits, misses = match([c for c in cands if span[0] <= c.onset_s <= span[1]], gts)
    pilot_report("1011 word-initial", hits, misses, cands, gts, span)
    assert len(gts) == 30
    assert len(hits) >= 27, f"hit rate {len(hits)}/{len(gts)} below 90% floor"

def test_pilot_1114_intervocalic_report_only():
    from src.detect_bursts import detect_bursts, load_audio
    rel = F_1114[0]
    x, sr = load_audio(os.path.join(REPO, rel + ".WAV"))
    gts = gt_bursts(rel)
    span = annotated_span(rel)
    cands = [c for c in detect_bursts(x, sr) if span[0] <= c.onset_s <= span[1]]
    hits, misses = match(cands, gts)
    pilot_report("1114 intervocalic (report-only)", hits, misses, cands, gts, span)

def test_pilot_unannotated_layouts_run():
    from src.detect_bursts import detect_bursts, load_audio
    for rel, _ in (UNANNOTATED, F_1203):
        x, sr = load_audio(os.path.join(REPO, rel + ".WAV"))
        cands = detect_bursts(x, sr)
        print(f"{os.path.basename(rel)}: {len(cands)} candidates (whole file)")
        assert isinstance(cands, list)
```

- [ ] **Step 2: Run the pilot tests one at a time and SHOW the reports**

Run: `segmentation_venv/bin/python -m pytest tests/test_bursts_pilot.py::test_pilot_1011_word_initial -v -s`
Then 1114, then the unannotated pair. Capture the printed reports.

- [ ] **Step 3: If the 1011 floor fails: STOP and present the report**

Show the user the printed report (hit rate, error distributions, misses,
false alarms) and propose calibration options (which defaults to move, why)
or a floor adjustment. Do NOT change `src/detect_bursts.py` defaults in this
task without that decision. If the floor passes, note that and move on.

- [ ] **Step 4: Generate the demo artifacts**

Run:
```bash
segmentation_venv/bin/python -m src.detect_bursts "audio/initial stops/1011_spf3_word-initial_24.WAV" --out out/
segmentation_venv/bin/python -m src.detect_bursts audio/1202_spm37_word-initial.WAV --out out/
```
Verify `out/*_bursts.csv` and `out/*_proposed.TextGrid` exist and the proposed
grid re-reads cleanly: `segmentation_venv/bin/python -c "from src.textgrid import read_grid; read_grid('out/1011_spf3_word-initial_24_proposed.TextGrid'); print('ok')"`.

### Task 7: Final gate — full suite + docs polish

**Files:**
- Modify: `src/detect_bursts.py` (docstring only, if Task 6 calibrated defaults)
- Modify: `docs/GROUNDTRUTH.md` (append a short "Pilot results (date)" section with the stock-default numbers)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Full suite**

Run: `segmentation_venv/bin/python -m pytest tests/ -q`
Expected: all pass, shown output.

- [ ] **Step 2: Docstring truthfulness**

If any default changed in Task 6, update the module docstring's default-value
list and the spec's "Left to the builder" note accordingly. If none changed,
no edit.

- [ ] **Step 3: GROUNDTRUTH.md pilot-results section**

Append: date, defaults used, per-recording hit rate / onset error / false
alarms, and any follow-ups (e.g. "asked M. for burst annotations on 1202/1203").
