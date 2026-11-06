# Pipeline technical reference

## Commands

| Command | Purpose | Key options |
|---|---|---|
| `python -m pipeline segment <wav>` | VAD → clips + grids + manifest | `--pad-ms 300` `--min-speech-ms 250` `--threshold 0.5` `--out out` `--force` |
| `python -m pipeline merge <out_dir>` | annotated clip grids → master grid | — |
| `python -m pipeline validate <grid_or_out_dir>` | annotation lint (exit 1 on errors) | — |
| `python -m pipeline measure <out_dir> --csv out.csv` | per-stop measures → CSV | `--window-ms 40` `--cep-n 12` `--audio <wav>` |

## Output layout & naming

```
out/<recording>/
├── manifest.json          bookkeeping + provenance (source of truth)
├── vad_raw.json           final VAD segments in seconds
├── master/
│   └── <name>.TextGrid    whole-recording grid, Utterance tier pre-filled
├── clips/
│   ├── seg0042_t0012300-0015600.wav          times in ms, zero-padded
│   └── seg0042_t0012300-0015600.TextGrid     rebased to [0, clip duration]
└── merge_report.json      written by `merge` (conflicts + timestamp)
```

Two id spaces exist on purpose:

- **master Utterance labels**: short ids `seg_0001 …` (stable per position).
- **clip filenames / manifest ids**: long ids `seg0042_t<start_ms>-<end_ms>`,
  self-describing without consulting the manifest.

### VAD parameters and their effects

| Param | Default | Meaning |
|---|---|---|
| `pad_ms` | 300 | Silero `speech_pad_ms`: margin added around each detected speech run so boundary stops (burst/voicing) are never clipped from a clip |
| `min_speech_ms` | 250 | Silero minimum speech duration; shorter runs are dropped as noise |
| `threshold` | 0.5 | Silero speech probability threshold |

Timestamps are taken in **samples** at Silero's internal 16 kHz and converted to
seconds (≈0.06 ms resolution), not the 0.1 s you get from `return_seconds=True`.
Padded runs that overlap are merged (`pipeline.vad.merge_intervals`) so clips
never overlap.

## TextGrid tier conventions

| # | Tier | Type | Filled by | Content |
|---|---|---|---|---|
| 1 | `Utterance` | IntervalTier | pipeline | segment ids (master) / clip id (clips); never edited by hand, never touched by `merge` |
| 2 | `Word` | IntervalTier | student | word transcription |
| 3 | `Sound` | IntervalTier | student | one labelled box per stop (`t b p q k d ɡw kw qw …`) |
| 4 | `Events` | IntervalTier | student | marker boxes labelled exactly `CO`, `BR`, `VO` |

**Why Events is an interval tier, not a point tier:** `praat-textgrids` cannot
serialise point tiers, and short boxes are no harder to place in Praat than
points. A marker's time = **midpoint of its box**, so width does not matter.

### Marker → stop assignment (`pipeline.textgrid.assign_markers`)

Student-drawn stop boxes cover closure+burst only, but voicing onset runs into
the following vowel. A marker is assigned to a stop if its midpoint falls in
`[stop.xmin − 0.15 s, stop.xmax + 0.35 s]`; if several stops claim it, the
nearest wins. Unassigned markers are reported by `validate`.

## Measurements (`pipeline measure`)

One CSV row per labelled `Sound` interval. Missing markers → empty cells (never
wrong numbers). Column reference:

| Column | Definition |
|---|---|
| `t_co_s`, `t_br_s`, `t_vo_s` | marker midpoints, seconds (recording time base) |
| `closure_ms` | `(BR − CO) × 1000` — stop closure duration |
| `vot_ms` | `(VO − BR) × 1000` — **signed**: positive = voicing after burst; negative = pre-voiced (expected for voiced stops) |
| `burst_ms_est` | heuristic transient length around BR, see below |
| `spec_centroid_hz`, `spec_spread_hz`, `spec_skewness`, `spec_kurtosis` | moments of the magnitude spectrum over `[BR, BR + window]` |
| `c00 … c11` | first 12 real-cepstrum coefficients of the same window |
| `burst_ms_manual` | empty column for a spectrogram-based manual override if you distrust the estimate |

Defaults: `window-ms = 40`, `cep-n = 12`.

### Spectral moments (formulas)

For the Hann-windowed analysis window, magnitude spectrum `S(f)`:

```
centroid = Σ f·|S| / Σ |S|            (Hz)
spread   = sqrt( Σ (f−μ)²·|S| / Σ|S| ) (Hz)
skew     = Σ (f−μ)³·|S| / (Σ|S| · spread³)
kurtosis = Σ (f−μ)⁴·|S| / (Σ|S| · spread⁴)
```

### Cepstrum (formula)

Real cepstrum of the log power spectrum: `c = IFFT( log( 1 + |FFT(x)|² ) )`,
first `n` coefficients kept (`c00` is mean log power). This is an **FFT
cepstrum**, not Praat's LPC quefrency — do not mix the two in analysis.

### Burst duration estimate (heuristic)

Short-time spectra (10 ms frames, 2 ms hop) from `BR − 20 ms` to `BR + 80 ms`;
spectral flux = Σ max(0, Sₖ − Sₖ₋₁). The burst region is the contiguous run of
frames whose flux exceeds `baseline + 4·std` (baseline = pre-burst frames),
starting at/after BR. Result clamped to ≤150 ms; if no clear transient is found
the cell is left empty → measure manually on the spectrogram and fill
`burst_ms_manual`. Treat `burst_ms_est` as a starting value, not ground truth.

## Manifest schema (`manifest.json`)

```jsonc
{
  "schema": 1,
  "created": "2026-…Z",
  "source": {
    "path": "audio/1203_spm37_intervocalic.WAV",   // as given on the command line
    "sha256": "…",                                  // provenance + change detection
    "sample_rate": 44100,
    "channels": 1,
    "duration_s": 131.63102
  },
  "params": {                                        // VAD settings that produced this run
    "pad_ms": 300, "min_speech_ms": 250, "threshold": 0.5,
    "silero_vad": "6.2.1", "torch": "2.13.0"
  },
  "master_textgrid": "master/1203_spm37_intervocalic.TextGrid",
  "segments": [
    { "id": "seg0001_t0000020-0004332",
      "start_s": 0.02, "end_s": 4.332,
      "clip": "clips/seg0001_t0000020-0004332.wav",
      "textgrid": "clips/seg0001_t0000020-0004332.TextGrid" }
  ]
}
```

**Id-stability guard:** `segment` refuses to write into an existing out dir if
the source sha256 or any VAD param differs (segment ids would shift and orphan
annotations); pass `--force` to override deliberately.

## Merge semantics (`pipeline merge`)

For each manifest segment, labelled intervals from the clip grid's `Word`,
`Sound` and `Events` tiers are offset by the segment start time and inserted
into the master tier at all shared boundary times:

- empty vs label → label wins (obviously)
- label vs label, equal → kept once
- label vs label, different → **clip wins**, recorded in `merge_report.json`
  under `conflicts` (inspect these!)
- adjacent same-label intervals are coalesced; the `Utterance` tier is never
  modified

Round-trip property (covered by `tests/test_merge_roundtrip.py` on the real
1203 annotation): splitting a master into clip grids and merging back preserves
all labelled content that lies inside segment spans exactly.

## Validate rules (`pipeline validate`)

Errors (exit code 1):
- unknown label on Events tier (must be CO/BR/VO)
- stop missing any of CO/BR/VO
- duplicate marker for one stop
- `CO` midpoint not before `BR` midpoint

Warnings:
- marker box wider than 100 ms (probably mis-drawn)
- |VOT| > 150 ms, closure > 300 ms (sanity checks — may be legitimate, review)
- stop outside any labelled Word interval (only when the Word tier has labels)
- marker not near any labelled stop

## Praat compatibility notes

- Generated grids: long-text format, UTF-8, header `xmin/xmax` derived from
  tier contents (praat-textgrids leaves them at 0 for in-memory grids — we fix
  that in `pipeline.textgrid.write_grid`).
- Reading back works for all Praat flavours incl. the **UTF-16BE** files Praat
  saves on macOS (verified against the real grids in `audio/`); any encoding is
  normalised by `praat-textgrids`.
- `praat_scripts/stop_measures.praat` prints VOT/closure for visual
  cross-checking inside Praat. It uses standard TextGrid methods only and does
  no file I/O; the Python engine remains the source of truth.

## Design decisions & trade-offs

- **Both master and clip grids** (student's choice): costs a merge step, buys
  flexibility (long-file context vs small manageable units / parallel annotators).
- **`praat-textgrids` over `praatIO`**: pure Python, no Praat binary needed to
  *produce* artifacts; Praat stays in the loop only where it must be (human
  annotation). GPL v3 is acceptable for internal research use.
- **No audio processing** (no resample/normalize): measurements are rate
  sensitive and the corpus is already uniform (44.1 kHz mono PCM16).
- **Events as interval tier**: see tier conventions above (library limitation +
  student ergonomics).
