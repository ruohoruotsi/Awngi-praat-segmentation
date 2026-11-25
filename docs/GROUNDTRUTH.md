# Ground Truth: Annotated Recordings in `audio/`

Surveyed 2026-11-24. All recordings are 44.1 kHz mono PCM16 elicitation sessions:
one word at a time, ~1.5–4 s silence between words.

| File | Layout (tiers, in order) | Encoding | Words | Burst ground truth |
|------|--------------------------|----------|-------|--------------------|
| `initial stops/1011_spf3_word-initial_24` (141 s) | word, consonant, vowel, **burst**, VOT | UTF-8 | 30 | **30 boxes, 2.1–15.0 ms, mean 6.8 ms** |
| `intervocalic stops/1114_spm32_intervocalic-19` | word, consonant, vowel, closure, **burst**, VOT | UTF-8 | 4 | 2 boxes, 3.4–6.9 ms |
| `1202_spm37_word-initial` (125 s) | Sound, Word (older layout) | UTF-16BE | 30 | none — ask M. for burst annotations |
| `1203_spm37_intervocalic` | Sound, Word (older layout) | UTF-16BE | 30 | none — ask M. for burst annotations |

## Conventions (M.'s layout — outputs must adhere)

- Tier names: lowercase `word`, `consonant`, `vowel`, `burst`; uppercase `VOT`;
  intervocalic files add `closure`.
- **Burst = a tiny IntervalTier box** (2–15 ms wide) marking the release region;
  it sits at the end of the `consonant` box (release point).
- Labels:
  - `consonant` tier: `<place><labialisation><token-repetition>`, e.g. `kʷ1`, `d2`
  - `burst` tier: `<consonant-label>_br`, e.g. `kʷ1_br`
  - `vowel` tier: `<consonant-label>_a<rep>`, e.g. `kʷ_a1`
  - `VOT` tier: `<consonant-label>_VOT`
  - `closure` tier (intervocalic only): `<consonant-label>_clo`
- `BR` in the legacy V1 code (CO/BR/VO event markers) == the `burst` tier concept.

## Known annotation warts (1011)

- A few burst labels drop the repetition number (`t_br`, `kʷ_br`).
- One hyphen instead of underscore (`d2-br`).
- Tooling must read labels leniently and never rewrite them.

## Coverage note

The annotated word spans do not cover the whole file: 1011 has ~25 s of
speech-level audio before the first word and ~30 s after the last; 1114 has
unannotated speech across most of its 131 s. Detections there are real words,
just unannotated — report them, don't treat them as false alarms.
