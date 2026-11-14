# Awngi Stop-Consonant Research

## Updated Plan 2026 Nov 7th
- After discussing the initial version with M., we need to find a way to localize all burst 
& VOT (pre vowel) regions.
- Rather than per-utterance segmentation, we simply need Praat TextGrids with these features accurately identified


## Quickstart

Requirements: Python 3.10+, [ffmpeg] on PATH, macOS/Linux.

```bash
python3.10 -m venv segmentation_venv
source segmentation_venv/bin/activate
pip install -r requirements.txt

# 1) segment a recording (VAD -> clips + Praat grids + manifest)
python -m pipeline segment audio/1203_spm37_intervocalic.WAV
```



## Repository layout

```
AGENTS.md                  project status & context for AI-assisted sessions
audio/                     real recordings + the student's original TextGrids
pipeline/                  the pipeline package (CLI: python -m pipeline …)
  vad.py                   Silero VAD, sample-precision timestamps, pad+merge
  segments.py              ffmpeg clip cutting + naming
  textgrid.py              Praat TextGrid generation / rebase (praat-textgrids)
  manifest.py              JSON bookkeeping + provenance + id-stability guard
  validate.py              annotation consistency lint
  measure/                 measurement engine (tiers -> CSV, DSP features)
examples/                  worked example grid + sample measures.csv
tests/                     pytest suite (round-trips on the REAL data)
out/                       generated output (gitignored)
silero_segment.py          original baseline script (kept for reference)
```

## Tests

```bash
python -m pytest tests/ -q
```

The suite validates the pipeline on the real recordings in `audio/` &rarr;
segmentation determinism, TextGrid integrity, Praat-format round-trips

## Notes

- Audio is never resampled or normalised: clips keep the source format
  (44.1 kHz mono PCM16), which Praat expects for native-rate analysis.
- TextGrids are written in Praat long-text format (UTF-8); the tools read back
  every Praat flavour, including the UTF-16 files Praat itself saves on macOS.
- `praat-textgrids` is GPLv3 — fine for internal research use.
- `silero_segment.py` predates this pipeline and is kept as a baseline reference.

[ffmpeg]: https://ffmpeg.org/  (e.g. `brew install ffmpeg`)
