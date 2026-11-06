"""Generate examples/1203_example_annotated.TextGrid.

Takes the student's REAL Sound + Word annotation of the first ~3 stops from
audio/1203_spm37_intervocalic.TextGrid and adds ILLUSTRATIVE placeholder CO /
BR / VO markers (CO at interval start, BR +40 ms, VO +100 ms) so a new
annotator can see exactly what a finished stop looks like.

The marker values are NOT measurements - replace them with your own.
Run:  python examples/make_example.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import textgrids

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "audio", "1203_spm37_intervocalic.TextGrid")
OUT = os.path.join(ROOT, "examples", "1203_example_annotated.TextGrid")


def main(n_stops=3):
    src = textgrids.TextGrid(SRC)
    duration = float(src["Sound"][-1].xmax)

    sound_spans = [(iv.xmin, iv.xmax, str(iv.text)) for iv in src["Sound"] if str(iv.text).strip()]
    word_spans = [(iv.xmin, iv.xmax, str(iv.text)) for iv in src["Word"] if str(iv.text).strip()]
    stops = sound_spans[:n_stops]

    event_spans = []
    for a, b, label in stops:
        co = (a + 0.005, a + 0.015, "CO")
        br = (a + 0.045, a + 0.055, "BR")
        vo = (a + 0.105, a + 0.115, "VO")
        event_spans += [co, br, vo]

    from pipeline.manifest import load_manifest
    from pipeline.textgrid import _interval_tier, write_grid

    # Utterance tier: real VAD segment ids if the pipeline has been run
    utterance_spans = []
    manifest = load_manifest(os.path.join(ROOT, "out", "1203_spm37_intervocalic"))
    if manifest:
        for i, s in enumerate(manifest["segments"]):
            utterance_spans.append((s["start_s"], s["end_s"], "seg_%04d" % (i + 1)))

    grid = textgrids.TextGrid()
    grid["Utterance"] = _interval_tier(duration, utterance_spans)
    grid["Word"] = _interval_tier(duration, word_spans)
    grid["Sound"] = _interval_tier(duration, sound_spans)
    grid["Events"] = _interval_tier(duration, event_spans)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    write_grid(grid, OUT)
    print("wrote %s (%d stops with placeholder markers)" % (OUT, n_stops))


if __name__ == "__main__":
    main()
