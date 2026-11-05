"""DSP features: spectral moments, cepstral coefficients, burst-duration estimate.

Conventions (documented in docs/pipeline.md):
- Spectral moments are the weighted first four moments of the Hann-windowed
  magnitude spectrum over a short analysis window (centroid Hz, spread Hz,
  skewness, kurtosis).
- Cepstrum is the real cepstrum of the log power spectrum (FFT cepstrum),
  NOT Praat's LPC quefrency; c0 is mean log power.
- Burst duration is a heuristic estimate from short-time spectral flux around
  the BR marker: contiguous frames whose flux exceeds a pre-burst baseline +
  4*std, starting at/after the burst. Treat as an estimate - the CSV carries a
  manual-override column for spectrogram-based measurement.
"""

import numpy as np


def window_signal(x, sr, t_start, duration):
    """Slice ``x`` (mono float samples) to [t_start, t_start+duration]."""
    i0 = max(0, int(round(t_start * sr)))
    i1 = min(len(x), int(round((t_start + duration) * sr)))
    return x[i0:i1]


def spectral_moments(x, sr):
    """Return (centroid_hz, spread_hz, skewness, kurtosis) or None if unusable."""
    if len(x) < 16:
        return None
    w = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x * w))
    freqs = np.fft.rfftfreq(len(x), d=1.0 / sr)
    weight = spec
    total = weight.sum()
    if total <= 0:
        return None
    centroid = float((freqs * weight).sum() / total)
    dev = freqs - centroid
    m2 = float((dev ** 2 * weight).sum() / total)
    spread = np.sqrt(m2)
    if spread <= 1e-9:
        return (centroid, 0.0, 0.0, 0.0)
    skew = float((dev ** 3 * weight).sum() / (total * spread ** 3))
    kurt = float((dev ** 4 * weight).sum() / (total * spread ** 4))
    return (centroid, float(spread), skew, kurt)


def cepstrum_coeffs(x, sr, n):
    """First ``n`` real-cepstrum coefficients of the windowed log power spectrum."""
    if len(x) < 16:
        return [0.0] * n
    w = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x * w))
    power = spec ** 2
    power[0] = max(power[0], 1e-12)
    cep = np.fft.irfft(np.log(power), n=len(x))
    return [float(c) for c in cep[:n]]


def estimate_burst_duration(x, sr, t_burst, win_ms=10.0, hop_ms=2.0, max_ms=150.0):
    """Heuristic burst transient length (seconds) starting at/after t_burst.

    Returns None when no clear transient is found (student measures manually).
    """
    frame = max(16, int(win_ms / 1000.0 * sr))
    hop = max(4, int(hop_ms / 1000.0 * sr))
    t0 = max(0.0, t_burst - 0.02)
    t1 = min(len(x) / sr, t_burst + 0.08)
    centers = []
    fluxes = []
    i = int(round(t0 * sr))
    while i + frame <= len(x):
        seg = x[i:i + frame] * np.hanning(frame)
        spec = np.abs(np.fft.rfft(seg, n=2 * frame))
        centers.append((i + frame / 2.0) / sr)
        fluxes.append(spec)
        i += hop
    if len(fluxes) < 4:
        return None
    flux = [float(np.maximum(0.0, f[1:] - p[1:]).sum()) for p, f in zip(fluxes, fluxes[1:])]
    baseline = float(np.mean(flux[:2]))
    sd = float(np.std(flux[:2])) + 1e-12
    thresh = max(baseline + 4.0 * sd, 1e-9)

    # first active frame at/after the burst time
    start_idx = None
    for k, c in enumerate(centers):
        if c >= t_burst and flux[k] > thresh:
            start_idx = k
            break
    if start_idx is None:
        return None
    end_idx = start_idx
    gap = 0
    for k in range(start_idx + 1, len(flux)):
        if flux[k] > thresh:
            end_idx = k
            gap = 0
        else:
            gap += 1
            if gap > 2:
                break
    first_start = (centers[start_idx] - win_ms / 2000.0) * sr
    last_end = (centers[end_idx] + win_ms / 2000.0) * sr
    dur_s = (last_end - first_start) / sr
    if not (0 < dur_s <= max_ms / 1000.0):
        return None
    return float(dur_s)
