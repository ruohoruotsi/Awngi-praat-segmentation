# Design: Analytic Burst Detection (word-initial Awngi stops, Phase 1a)

Date: 2026-11-24. Status: approved in conversation; builder-check questions resolved
as stated below. See `docs/GROUNDTRUTH.md` for the data survey.

## Intent and why

M. has ~3,840 speech tokens to annotate (docs/RESEARCH.md). Phase 1 = word-initial
stops: the system proposes release-burst boundaries, M. verifies in Praat
(semi-automatic, human keeps final control). Burst localization is the foundation
for VOT and per-burst acoustic feature extraction, so it comes first.

Deliberate constraint: **analytic DSP only, no SSL speech representations.**
The detector is inspired by madmom's super-flux (positive spectral difference),
re-implemented at speech transient time-scales — madmom's own params
(~93 ms hop @ 11 kHz) target beat tempo and are far too coarse for ±5 ms
burst boundaries.

## Data and ground truth

See docs/GROUNDTRUTH.md. Key facts:

- Quantitative ground truth: the `burst` tier of `1011_spf3_word-initial_24`
  (30 boxes, 2.1–15.0 ms, mean 6.8 ms) — primary; `1114_spm32_intervocalic-19`
  (2 boxes) — secondary/report-only.
- `1202`/`1203` (older Sound+Word layout) have no burst annotations: detector
  runs on them for robustness/demo, no quantitative validation. M. will be asked
  for more annotated files.
- Annotated word spans do not cover the whole file; large unannotated speech
  regions exist. Detections there are real (unannotated) words.

## Goals

1. New module `src/detect_bursts.py`: audio → candidates with onset (s), offset
   (s), duration (ms), score, confidence ∈ [0,1].
2. Per-recording deliverables:
   - `<stem>_bursts.csv` — one row per candidate, all fields, whole file.
   - `<stem>_proposed.TextGrid` — input tiers copied as-is + a proposal tier with
     one short box (min ~5 ms wide, editable) per candidate.
3. Pilot validation against the `burst` tiers (1011 primary, 1114 report-only):
   hit rate, onset/offset error (ms), false alarms.

## Non-goals / anti-goals (this effort)

- No VOT, no closure voicing, no vowel detection — next effort.
- No SSL / learned representations; no madmom dependency.
- No resampling or normalisation (repo convention: native rate, source format).
- No tier-scheme migration for the 1202/1203 files; no scaffold grids for
  unannotated recordings (follow-up).
- No git commits — changes stay in the working tree.

## Constraints

- Python 3.10+, existing deps only: numpy, scipy, soundfile, praat-textgrids, pytest.
- TDD per AGENTS.md: tests first, run one at a time, show each output.
- Fresh-eyes code review of the branch before "done".
- Initial evaluation uses stock defaults — no tuning to the ground truth first
  (user directive: see how the initial algo does).

## Approaches considered

| # | Approach | Trade-off | Outcome |
|---|----------|-----------|---------|
| A | Short-frame spectral flux (super-flux style re-implementation): 5 ms Hann frames, ~2.3 ms hop, positive magnitude difference, high-pass freq weighting, two-stage adaptive threshold, peak picking, duration veto | ms resolution, pure numpy/scipy, every knob explainable | **Chosen** |
| B | Time-domain HPF → rectify → envelope → threshold | Simplest; weaker burst-vs-vowel-onset separation, weaker confidence signal | Rejected as core |
| C | madmom `SuperfluxFeature` coarse gating + custom fine pass | 93 ms core resolution; dependency adds nothing A doesn't cover | Rejected |

## Design: module `src/detect_bursts.py`

```python
load_audio(path) -> (x: np.ndarray[float64], sr: int)
burst_flux(x, sr, frame_ms=5.0, hop_ms=2.3, fc0=500.0, fc1=1500.0) -> (times, flux)
detect_bursts(x, sr, **params) -> list[Burst]   # Burst: onset_s, offset_s, score, confidence
write_proposed_grid(in_grid_path, out_path, bursts, duration)
main(argv)  # CLI
```

Signal chain:

1. Frames: Hann 5 ms (220 samples @ 44.1 k), hop ~2.3 ms (~100 samples, ~435
   frames/s), rfft magnitude.
2. `flux[t] = Σ_b max(0, |S[t+1,b]| − |S[t,b]|) · w(f)`; w(f) = 0 below fc0
   (default 500 Hz), linear ramp to 1 at fc1 (default 1.5 kHz). Low fc0 on
   purpose: labial bursts have low centroid; 500 Hz still removes most
   voiced-segment energy.
3. Threshold: coarse global = median(flux) + k·MAD(flux), k default 5 (long
   inter-word silences pin the median). Local: per surviving peak, baseline =
   median/MAD over ±0.5 s neighbourhood.
4. Peak picking: local maxima above coarse threshold; min gap 100 ms; candidate's
   contiguous above-local-threshold region must be 3–150 ms (rejects
   vowel-onset ramps; GT bursts are 2–15 ms).
5. Onset = rising edge: last frame below (local baseline + 1·MAD) immediately
   before the flux rise. Offset = last frame above local threshold, 2-frame gap
   tolerance.
6. Confidence ∈ [0,1], monotone in clarity, one-line explainable. Inputs: local
   prominence, duration sanity (penalise near the 150 ms veto edge), post-burst
   50 ms decay. Exact formula = builder's call.

CLI:

```
python -m src.detect_bursts <wav> --out out/
# writes <out>/<stem>_bursts.csv and <out>/<stem>_proposed.TextGrid (if a
# co-located <stem>.TextGrid exists next to the WAV)
# flags: --fc0 --fc1 --k --min-gap --max-burst-ms --no-grid
```

## Builder-check resolutions (stated calls, correctable)

1. **Proposal tier name**: if the input grid already has a `burst` tier (the GT
   files do), proposals go to a **`burst_auto`** tier (placed where `burst`
   would sit, i.e. before `VOT`); if not, they go to `burst`. Never overwrite an
   existing tier. For the pilot files this stacks M.'s `burst` vs the tool's
   `burst_auto` in Praat — ideal for visual verification.
2. **Unannotated speech regions**: detector runs whole-file (proposals there are
   real unannotated words — the point of the tool). Pilot evaluation is
   restricted to the annotated span (union of `word` tier boxes ± 1 s margin);
   whole-file detections are reported separately, not counted as false alarms.
3. **Hit-rate floor**: pooled over 1011's 30 GT bursts only (initial floor
   ≥ 90 % → ≥ 27/30). 1114 (2 bursts, intervocalic) is report-only.
4. **score vs confidence**: `score` = local prominence of the peak in MAD units
   (peak − local baseline, divided by local MAD) — absolute, for diagnostics
   across recordings. `confidence` = normalized [0,1] monotone transform used
   for grid labels. CSV also carries the raw peak flux value.
5. **No co-located TextGrid**: CSV-only mode, no error, no scaffold grid
   (scaffolding deferred).
6. TP matching: 1:1 greedy, nearest GT box by onset; TP iff onset ∈
   [gt.xmin − 10 ms, gt.xmax + 10 ms].
7. `segmentation_venv` goes in `.gitignore`.

## Tests

Synthetic (`tests/test_detect_bursts.py`), TDD one at a time:

1. silence → zero detections
2. 30 ms broadband noise pulse in silence at known t → detected, onset ±5 ms,
   offset ±10 ms
3. sustained 2 kHz tone → zero detections
4. weak labial-like burst (~1 kHz-centroid, low level) → detected at defaults
   (guards against fc0 too high)
5. vowel-onset-like ramp (rising formant sweep after silence) → not detected
6. two pulses 0.5 s apart → both detected, correct order
7. confidence ordering: strong burst > weak burst

Pilot (`tests/test_bursts_pilot.py`, real data): read the `burst` tier of 1011
and 1114; evaluate within the annotated span only; report per-recording hit
rate, onset/offset error ms, false alarms (no GT box within 50 ms); assert the
1011 floor; 1114 reported. Thresholds tightened only after the first
stock-default run — per the "see how the initial algo does" directive.

## Housekeeping (minimal)

1. `src/__init__.py` (empty) so `python -m src.detect_bursts` works.
2. Fix `src/measure_grid.py` broken `from ..textgrid import assign_markers`
   → `from .textgrid import ...` (`run_measure`'s `..manifest` reference is
   call-time only; follow-up).
3. Rewrite `tests/conftest.py`, `tests/test_measure.py`, `tests/test_validate.py`
   (import the deleted `pipeline.*`) → `src.*`; drop the unused `seg_output`
   fixture.
4. `requirements.txt`: drop V1 leftovers (runez, torchcodec, silero-vad).
5. README quickstart: replace stale `auto_annotate` with `detect_bursts`.
6. `.gitignore`: add `segmentation_venv/`.
7. Environment: `python3.10 -m venv segmentation_venv && pip install -r requirements.txt`.

## Left to the builder

- Exact confidence formula (monotone, [0,1], one-line explainable).
- Linear vs log-magnitude flux (start linear).
- Final default parameters, calibrated only after the stock-default pilot
  report; document chosen values in the module docstring.

## Risks

- Weak/absent releases → no detection; CSV makes it visible; acceptable for a
  proposal tool.
- 32 annotated bursts is a small quantitative basis; more files requested from M.
- Vowel-onset bump right after a burst → min gap + duration veto; watch pilot FAs.
