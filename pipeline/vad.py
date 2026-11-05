"""Silero VAD segmentation with sample-precision timestamps.

Timestamps are taken in samples (16 kHz internally) and converted to seconds,
giving ~0.06 ms resolution instead of the 0.1 s you get from return_seconds=True.
"""

import soundfile as sf


def load_model():
    import torch

    torch.set_num_threads(1)  # deterministic inference
    from silero_vad import load_silero_vad

    return load_silero_vad()


def run_vad(wav_path, model=None, pad_ms=300, min_speech_ms=250, threshold=0.5):
    """Return a sorted list of (start_s, end_s) speech segments for wav_path."""
    from silero_vad import get_speech_timestamps, read_audio

    if model is None:
        model = load_model()
    wav = read_audio(wav_path)  # mono 16 kHz tensor
    stamps = get_speech_timestamps(
        wav,
        model,
        threshold=threshold,
        sampling_rate=16000,
        min_speech_duration_ms=min_speech_ms,
        speech_pad_ms=pad_ms,
        return_seconds=False,  # sample precision
    )
    duration = sf.info(wav_path).duration
    segs = [(int(s["start"]) / 16000.0, int(s["end"]) / 16000.0) for s in stamps]
    segs = [(max(0.0, a), min(duration, b)) for a, b in segs if b > a]
    return merge_intervals(segs)


def merge_intervals(segs, gap=0.0):
    """Sort and merge overlapping or touching intervals."""
    out = []
    for a, b in sorted(segs):
        if out and a <= out[-1][1] + gap:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out
