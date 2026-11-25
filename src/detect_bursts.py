"""Analytic release-burst detector for stop consonants.

Super-flux style (madmom-inspired) positive spectral difference, re-implemented
at speech transient time-scales. Analytic DSP only - no SSL representations.

Signal chain:
  1. Hann frames (default 5 ms, hop ~2.3 ms), rfft magnitudes
  2. flux[t] = sum_b max(0, |S[t+1,b]| - |S[t,b]|) * w(f)
     with w(f) = 0 below fc0 (500 Hz), linear ramp to 1 at fc1 (1.5 kHz)
  3. two-stage adaptive threshold: global median + k*MAD, then a local
     +/-0.5 s baseline around each surviving peak
  4. peak picking: min inter-candidate gap, duration veto (3-150 ms)
  5. onset = rising edge, offset = last active frame (2-frame gap tolerance)
  6. confidence = score / (score + 10) clipped to [0, 1]

Current defaults: frame_ms=5.0, hop_ms=2.3, fc0=500.0, fc1=1500.0, k=5.0,
min_gap_s=0.1, min_burst_ms=3.0, max_burst_ms=150.0
"""

import numpy as np


def burst_flux(x, sr, frame_ms=5.0, hop_ms=2.3, fc0=500.0, fc1=1500.0):
    """High-pass-weighted positive spectral flux.

    Returns (times, flux): ``times`` are the frame-center times (seconds) of
    the frames that have a successor, so ``len(times) == len(flux)``.
    """
    frame = max(16, int(round(frame_ms / 1000.0 * sr)))
    hop = max(1, int(round(hop_ms / 1000.0 * sr)))
    if len(x) < frame * 2:
        return np.array([]), np.array([])
    n_frames = 1 + (len(x) - frame) // hop
    win = np.hanning(frame)
    S = np.empty((n_frames, frame // 2 + 1))
    for i in range(n_frames):
        S[i] = np.abs(np.fft.rfft(x[i * hop:i * hop + frame] * win))
    freqs = np.fft.rfftfreq(frame, d=1.0 / sr)
    w = np.clip((freqs - fc0) / (fc1 - fc0), 0.0, 1.0)
    flux = np.maximum(0.0, S[1:] - S[:-1]) @ w
    times = (np.arange(len(flux)) * hop + frame / 2.0) / sr
    return times, flux
