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

# 1) burst detection -> candidates CSV + proposal TextGrid
python -m src.detect_bursts audio/1203_spm37_intervocalic.WAV --out out/
```



## Repository layout

```
audio/                Real recordings + the original TextGrids
docs/                 Tutorial, extra documentation, linguistics context or Praat help 
src/                  Main source code
  detect_bursts.py    Burst detector (spectral flux, adaptive threshold)
  textgrid.py         Praat TextGrid generation, using praat-textgrids
  features.py         Compute a few Audio DSP features
  measure_grid.py     Extract per-stop acoustic measures from an annotated master TextGrid.
  validate.py         Annotation consistency check
tests/                pytest suite (round-trips on the REAL data)
out/                  Generated output TextGrids (gitignored)
```

## Tests

```bash
python -m pytest tests/ -q
```

The suite validates the analysis and output of TextGrids 

## Notes

- Audio is never resampled or normalised: clips keep the source format
  (44.1 kHz mono PCM16), which Praat expects for native-rate analysis.
- TextGrids are written in Praat long-text format (UTF-8); the tools read back
  every Praat flavour, including the UTF-16 files Praat itself saves on macOS.
- `praat-textgrids` is GPLv3 — fine for internal research use.

[ffmpeg]: https://ffmpeg.org/  (e.g. `brew install ffmpeg`)
