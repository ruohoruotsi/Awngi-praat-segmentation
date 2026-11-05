"""Manifest: per-recording bookkeeping + provenance.

The manifest is the single source of truth mapping segment ids to clips,
grids and time spans. Re-running with different VAD parameters (which would
shift segment ids and orphan student annotations) is refused unless --force.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

SCHEMA = 1


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ManifestConflict(RuntimeError):
    pass


def load_manifest(out_dir):
    path = os.path.join(out_dir, "manifest.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def guard_existing(out_dir, params, src_wav):
    """Refuse to clobber a previous run whose inputs or parameters changed."""
    m = load_manifest(out_dir)
    if m is None:
        return
    old_params = m.get("params", {})
    old_src = m.get("source", {}).get("sha256")
    new_sha = sha256_file(src_wav)
    diffs = []
    for key in params:
        if old_params.get(key) != params[key]:
            diffs.append("%s: %r -> %r" % (key, old_params.get(key), params[key]))
    if old_src and old_src != new_sha:
        diffs.append("source file changed (sha256 mismatch)")
    if diffs:
        raise ManifestConflict(
            "refusing to re-segment into existing out dir %r:\n  %s\n"
            "use --force to overwrite (student annotations in grids would be lost)"
            % (out_dir, "\n  ".join(diffs))
        )


def write_manifest(out_dir, src_wav, params, segments, master_textgrid):
    import soundfile as sf

    info = sf.info(src_wav)
    manifest = {
        "schema": SCHEMA,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "path": src_wav,
            "sha256": sha256_file(src_wav),
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "duration_s": round(info.frames / float(info.samplerate), 6),
        },
        "params": params,
        "master_textgrid": master_textgrid,
        "segments": [
            {
                "id": s["id"],
                "start_s": round(s["start_s"], 6),
                "end_s": round(s["end_s"], 6),
                "clip": os.path.relpath(s["clip"], out_dir),
                "textgrid": os.path.relpath(s["textgrid"], out_dir),
            }
            for s in segments
        ],
    }
    path = os.path.join(out_dir, "manifest.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest
