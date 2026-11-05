"""CLI entry point.

    python -m pipeline.segment <wav> [--pad-ms 300] [--min-speech-ms 250]
                               [--threshold 0.5] [--out out] [--force]
    python -m pipeline.merge   <out_dir>
    python -m pipeline.validate <grid_or_out_dir>
    python -m pipeline.measure <out_dir> --csv measures.csv
                               [--window-ms 40] [--cep-n 12] [--audio wav]
"""

import argparse
import json
import os
import sys


def cmd_segment(args):
    from .manifest import ManifestConflict, guard_existing, write_manifest
    from .segments import extract_clips
    from .textgrid import build_clip_grid, build_master_grid, write_grid
    from .vad import load_model, run_vad

    src = args.wav
    if not os.path.exists(src):
        raise SystemExit("audio not found: %s" % src)
    base = os.path.splitext(os.path.basename(src))[0]
    out_dir = os.path.join(args.out, base)
    clips_dir = os.path.join(out_dir, "clips")
    master_dir = os.path.join(out_dir, "master")

    params = {
        "pad_ms": args.pad_ms,
        "min_speech_ms": args.min_speech_ms,
        "threshold": args.threshold,
        "silero_vad": _pkg_version("silero_vad"),
        "torch": _pkg_version("torch"),
    }
    if not args.force:
        guard_existing(out_dir, params, src)

    print("VAD on %s ..." % src)
    model = load_model()
    segs = run_vad(src, model, pad_ms=args.pad_ms,
                   min_speech_ms=args.min_speech_ms, threshold=args.threshold)
    if not segs:
        raise SystemExit("no speech segments found - check the audio/threshold")

    os.makedirs(clips_dir, exist_ok=True)
    os.makedirs(master_dir, exist_ok=True)
    print("cutting %d clips ..." % len(segs))
    clips = extract_clips(src, segs, clips_dir)

    duration = _wav_duration(src)
    master = build_master_grid(duration, segs)
    master_path = os.path.join(master_dir, base + ".TextGrid")
    write_grid(master, master_path)

    segments_info = []
    for i, clip in enumerate(clips):
        grid = build_clip_grid(clip["end_s"] - clip["start_s"], clip["id"])
        grid_path = os.path.join(clips_dir, clip["id"] + ".TextGrid")
        write_grid(grid, grid_path)
        segments_info.append({**clip, "textgrid": grid_path})

    manifest = write_manifest(out_dir, src, params, segments_info,
                              os.path.relpath(master_path, out_dir))
    with open(os.path.join(out_dir, "vad_raw.json"), "w") as f:
        json.dump([{"start_s": a, "end_s": b} for a, b in segs], f, indent=2)

    speech = sum(b - a for a, b in segs)
    print("\n%d segments  (%.1fs speech of %.1fs, %.0f%%)" %
          (len(segs), speech, duration, 100.0 * speech / duration))
    for s in segments_info[:5]:
        print("  %-28s %8.3f -> %8.3f" % (s["id"], s["start_s"], s["end_s"]))
    if len(segments_info) > 5:
        print("  ... (%d more)" % (len(segments_info) - 5))
    print("\noutput: %s\n  master grid: %s" % (out_dir, os.path.relpath(master_path)))


def cmd_merge(args):
    from .merge import run_merge

    report = run_merge(args.out_dir)
    print("merged %d clip tier(s); %d conflict(s)" %
          (report["segments_merged"], len(report["conflicts"])))
    for c in report["conflicts"]:
        print("  CONFLICT %s %s @%.3f: master=%r vs clip=%r -> clip wins" %
              (c["segment"], c["tier"], c["t_start"], c["master_label"], c["clip_label"]))


def cmd_validate(args):
    from .textgrid import read_grid
    from .validate import format_issues, validate_grid

    target = args.target
    if os.path.isdir(target):
        from .manifest import load_manifest

        m = load_manifest(target)
        if m is None:
            raise SystemExit("no manifest.json in %s" % target)
        grid_path = os.path.join(target, m["master_textgrid"])
    else:
        grid_path = target
    issues = validate_grid(read_grid(grid_path))
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    print("%s: %d error(s), %d warning(s)" % (grid_path, len(errors), len(warnings)))
    if issues:
        print(format_issues(issues))
    sys.exit(1 if errors else 0)


def cmd_measure(args):
    from .measure.extract import run_measure

    csv_path, n = run_measure(args.out_dir, args.csv,
                              window_s=args.window_ms / 1000.0, cep_n=args.cep_n,
                              audio_override=args.audio)
    print("wrote %d row(s) to %s" % (n, csv_path))


def _wav_duration(path):
    import soundfile as sf

    info = sf.info(path)
    return info.frames / float(info.samplerate)


def _pkg_version(name):
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return ""


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pipeline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("segment", help="VAD-segment a recording into clips + Praat grids")
    p.add_argument("wav")
    p.add_argument("--pad-ms", type=int, default=300)
    p.add_argument("--min-speech-ms", type=int, default=250)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--out", default="out")
    p.add_argument("--force", action="store_true", help="overwrite even if params/source changed")
    p.set_defaults(func=cmd_segment)

    p = sub.add_parser("merge", help="merge annotated clip grids into the master grid")
    p.add_argument("out_dir")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("validate", help="lint annotation consistency of a grid or out dir")
    p.add_argument("target")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("measure", help="extract per-stop acoustic measures to CSV")
    p.add_argument("out_dir")
    p.add_argument("--csv", default="measures.csv")
    p.add_argument("--window-ms", type=float, default=40.0)
    p.add_argument("--cep-n", type=int, default=12)
    p.add_argument("--audio", default=None, help="override source wav path")
    p.set_defaults(func=cmd_measure)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
