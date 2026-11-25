"""Synthetic tests for the analytic burst detector (no real audio)."""

import numpy as np
import pytest

pytestmark = pytest.mark.filterwarnings("ignore")

SR = 44100


def make_tone(sr, f0, t_start, duration=2.0, amp=0.5):
    t = np.arange(int(sr * duration)) / sr
    x = np.zeros_like(t)
    m = t >= t_start
    x[m] = amp * np.sin(2 * np.pi * f0 * t[m])
    return x


def test_flux_silence_is_zero():
    from src.detect_bursts import burst_flux
    times, flux = burst_flux(np.zeros(44100 * 2), SR)
    assert len(times) == len(flux) > 100
    assert flux.max() == 0.0


def test_flux_spikes_at_tone_onset_then_decays():
    from src.detect_bursts import burst_flux
    x = make_tone(SR, 2000.0, t_start=0.5)
    times, flux = burst_flux(x, SR)
    peak_i = int(np.argmax(flux))
    assert 0.48 < times[peak_i] < 0.56
    assert flux[(times > 0.7) & (times < 2.0)].max() < 1e-3 * flux[peak_i]


def make_pulse(x, t0, dur=0.030, amp=0.5, seed=0):
    i0, i1 = int(t0 * SR), int((t0 + dur) * SR)
    x[i0:i1] = amp * np.random.default_rng(seed).normal(0, 1, i1 - i0)
    return x


def test_silence_no_detections():
    from src.detect_bursts import detect_bursts
    assert detect_bursts(np.zeros(SR * 2), SR) == []


def test_noise_pulse_detected():
    from src.detect_bursts import detect_bursts
    x = np.zeros(SR * 2)
    make_pulse(x, 1.000, dur=0.030)
    b = detect_bursts(x, SR)
    assert len(b) == 1, b
    assert abs(b[0].onset_s - 1.000) <= 0.005, b[0].onset_s
    assert abs(b[0].offset_s - 1.030) <= 0.010, b[0].offset_s
    assert 0.0 < b[0].confidence <= 1.0


def test_steady_tone_no_detections():
    from src.detect_bursts import detect_bursts
    assert detect_bursts(make_tone(SR, 2000.0, t_start=0.0, duration=2.0), SR) == []


def test_flux_highpass_suppresses_lowband():
    from src.detect_bursts import burst_flux
    x = make_tone(SR, 200.0, t_start=0.5)   # below fc0 -> fully unweighted
    times, flux = burst_flux(x, SR)
    # steady state: the 200 Hz tone is 0.9977 periods per 220-sample window, so its
    # near-DC leakage phase-couples into weighted bins and oscillates ~1e-2 - still
    # ~1/5000 of a burst's flux. Any weight error would push this to O(1).
    steady = flux[(times > 0.55) & (times < 2.0)]
    assert steady.max() < 0.05, steady.max()
    # onset partial-window artifact stays small vs an in-band burst
    _, flux_hi = burst_flux(make_tone(SR, 2000.0, t_start=0.5), SR)
    assert flux.max() < 0.1 * flux_hi.max(), (flux.max(), flux_hi.max())
