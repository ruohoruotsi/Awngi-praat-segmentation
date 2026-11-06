# How to annotate your clips in Praat (step by step)

This guide is for **manual annotation** of Awngi stop consonants. The audio has
already been cut into short utterances automatically, so you are working with
small files instead of one long recording. Your job: mark the stops and their
key moments. Everything after that (measuring VOT, closure duration, spectral
moments, cepstral coefficients) is done by a script.

> **Keep it simple:** if in doubt, draw the box a little wide — we measure the
> *middle* of each marker box, so you do not need pixel-perfect timing boxes.

---

## 1. What you received

```
out/<recording>/
├── manifest.json              ← bookkeeping (you never edit this)
├── master/
│   └── <name>.TextGrid        ← the WHOLE recording, one grid
└── clips/                     ← short utterances (~1-5 s each)
    ├── seg0001_t0000020-0004332.wav
    ├── seg0001_t0000020-0004332.TextGrid   ← same name, goes with the wav
    ├── seg0002_t0004660-0006444.wav
    └── ...
```

Every clip `.wav` has a `.TextGrid` with **exactly the same name** next to it.
That is what lets Praat link them automatically (see step 2).

There are two ways to work — pick ONE and stick with it (ask your advisor):

| | A) master grid | B) clips |
|---|---|---|
| You open | the long wav + `master/<name>.TextGrid` | one short clip at a time |
| Pros | full context, single file | easy to handle, can split work between people |
| Cons | long file in Praat | after finishing, run `python -m pipeline merge <out_dir>` once so all clips are combined |

Both produce the same result. Clips are already cut around each utterance with
a margin, so no stop is chopped off at the edges.

---

## 2. Opening a file in Praat

1. In Praat: **File → Open...** and choose a `.wav` (clip or master).
2. Because the `.TextGrid` has the same name and sits in the same folder,
   Praat attaches it automatically. You should see both objects listed in the
   *Praat objects* window:

```
┌─ Praat objects ────────────────┐
│  Sound     seg0001_t...332.wav │
│  TextGrid  seg0001_t...332.TextGrid
└────────────────────────────────┘
```

3. Click the **Sound** object once, then **View and edit** (or double-click).
   The spectrogram + tier editor opens:

```
┌─ Praat picture window ─────────────────────────────────────────────┐
│  spectrogram (dark = energy)                                       │
│  ▒▒▒▒░░░░▓▓▓░░░░░░░░░▒▒▒▒▒▒▒▒                                     │
│  ░░▒▒▒░░  ▓▓  ░░░░░░░░░░░▒▒▒▒                                     │
│  ░░░▒▒░░░  ▓   ░░░░░░░▒▒▒▒▒                                       │
│────────────────────────────────────────────────────────────────────│
│  Utterance  [ seg0001_t0000020-0004332                    ]        │ ← don't touch
│  Word       [            kita              ]                        │ ← 1. words
│  Sound      [    |t|                       ]                        │ ← 2. stops
│  Events     [   (CO)  (BR)  (VO)          ]                         │ ← 3. markers
└────────────────────────────────────────────────────────────────────┘
```

The four tiers, top to bottom:

| Tier | What goes in it | Who fills it |
|---|---|---|
| **Utterance** | the clip's id (already there) | the pipeline — *do not edit* |
| **Word** | one word per box, e.g. `bɨtam` | you |
| **Sound** | one box per stop, labelled with its symbol: `t b p q k d ɡw kw qw …` | you |
| **Events** | three tiny marker boxes per stop: `CO`, `BR`, `VO` | you |

---

## 3. Drawing boxes (the only mouse skill you need)

- **Interval tiers (Word, Sound, Events):** click-drag on the tier line to draw
  a box; double-click the box to type its label; press Enter.
- To move/resize a box: drag its edges while holding the mouse.
- Marker boxes in **Events** should be *small* (about 10 ms wide is fine).
  We read the **middle** of the box, so do not stress about the width.

---

## 4. Marking one stop — where exactly?

Play the clip and watch the spectrogram. For each stop you will place:

```
        closure onset      burst / release       voicing onset
              CO                 BR                    VO
                 ↓                  ↓                   ↓
 time ──────────────┬──────────────────┬───────────────────┐
```

### The three moments, visually

**Voiceless stop (e.g. `t`, `p`, `k`) — voicing starts AFTER the burst:**

```
 high freq │         ░░▓▓▓                ← vertical stripe = BURST  → BR here
           │      ░░░ ▓▓▓
 mid       │ ────formants converge ▓▓▓    then a short gap (the VOT)
 low freq  │ ════════  ░░░░░░░  ▓▓▓ ░░░░░▒▒▒▒▒▒▒▒▒▒
           │ voice bars  quiet closure       voice bars come back → VO here
           └──────────┬─────────────┬───────────────────┬──────── time
                      CO            BR                  VO
```

- **CO (closure onset):** where the voice bars stop and the formants start
  converging into a dark gap.
- **BR (burst / release):** the bright vertical stripe on the spectrogram.
- **VO (voicing onset):** where horizontal voice bars reappear after the burst.
  The distance `VO − BR` is the VOT — it can be tens of milliseconds, that is
  normal for voiceless stops.

**Voiced / pre-voiced stop (e.g. `d`, `b`, `ɡ`) — voicing starts BEFORE or AT the burst:**

```
 high freq │              ░░▓▓▓            ← burst stripe → BR here
 mid       │        ░░░░  ▓▓▓
 low freq  │ ═════════════▒▒▒▓▓▓▒▒▒▒▒▒▒    voice bars keep going under the stop
           │              ↑
           └──────────────┴──────────────────────────────── time
                      VO (before or at BR)
```

- Put **VO** where the voice bars are clearly running *under* the closure, just
  before release. Here `VO − BR` is **negative** — that is a correct and
  expected result for voiced stops (pre-voicing), not an error.

### Quick checklist per stop

1. Sound tier: one box around the stop, label = phoneme (`t`, `ɡw`, …)
2. Events tier: three small boxes labelled exactly `CO`, `BR`, `VO`
   (capital letters, no spaces)
3. Word tier: the word this stop belongs to

---

## 5. Saving

- **File → Save** (or *Save as…*). Keep the file name unchanged — the grid must
  keep exactly the same name as its `.wav`.
- If Praat asks which format, choose **long text** (the default). Any format is
  readable by our tools, but long text is also human-readable.
- Do not rename or move files inside `clips/` or `master/`.

---

## 6. Checking your work (optional but recommended)

From the project folder in a terminal (with the environment activated):

```
python -m pipeline validate out/<recording>          # whole master grid
python -m pipeline validate out/<recording>/clips/seg0001_....TextGrid   # one clip
```

It lists problems like `stop 't' has no VO marker` or
`closure onset (CO) must precede burst (BR)`. Zero errors = ready to measure.
Warnings are sanity checks (very long closure, unusual VOT…) — look at those
cases once and decide if they are real.

A fully worked example on your own audio: open
`examples/1203_example_annotated.TextGrid` next to
`audio/1203_spm37_intervocalic.WAV`. The first three stops (`t`, `b`, `p`)
contain **placeholder** CO/BR/VO values so you can see the finished layout —
replace those boxes with your own measurements; every other stop in that file
is still empty and will be flagged by `validate` until annotated.

---

## 7. When everything is annotated

Tell iroro (or run it yourself):

```
python -m pipeline merge out/<recording>     # only needed if you worked per-clip
python -m pipeline validate out/<recording>  # final QA gate
python -m pipeline measure out/<recording> --csv measures.csv
```

`measures.csv` then has one row per stop with VOT, closure duration, burst
estimate, spectral moments and cepstral coefficients — ready for analysis.
