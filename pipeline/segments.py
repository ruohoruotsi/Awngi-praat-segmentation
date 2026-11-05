"""Cut per-utterance clips from the source WAV using ffmpeg.

PCM input means input seeking is sample-accurate, so we keep the fast
``-ss``-before-``-i`` form. Output stays in the source format (44.1 kHz mono
PCM16 for this corpus) - never resample or normalise: measurements are
sample-rate sensitive and Praat expects native rate.
"""

import os
import subprocess


def clip_name(index, start_s, end_s):
    """Stable, sortable name: seg0042_t0012300-0015600 (times in ms)."""
    return "seg%04d_t%07d-%07d" % (index, int(round(start_s * 1000)), int(round(end_s * 1000)))


def extract_clips(src_wav, segments, out_dir):
    """Cut one WAV per segment. Returns list of dicts: id/start_s/end_s/clip."""
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for i, (start, end) in enumerate(segments, start=1):
        cid = clip_name(i, start, end)
        out_path = os.path.join(out_dir, cid + ".wav")
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", "%.6f" % start,
            "-t", "%.6f" % (end - start),
            "-i", src_wav,
            "-y", out_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg failed for %s: %s" % (cid, proc.stderr.strip()))
        results.append({"id": cid, "start_s": start, "end_s": end, "clip": out_path})
    return results


def clip_duration(clip_path):
    import soundfile as sf

    info = sf.info(clip_path)
    return info.frames / float(info.samplerate)
