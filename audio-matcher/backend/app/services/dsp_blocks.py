"""Real DSP building blocks that stand in for VST3 plugin categories in
SimulatedPluginHost. Standard peaking-EQ cookbook biquads, feedforward RMS
compressor, tanh waveshaper, Schroeder reverb -- functional signal processing,
not placeholders, so the optimizer loop can be validated against real audio.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import lfilter


def _peaking_biquad(freq: float, gain_db: float, q: float, sr: int) -> tuple[np.ndarray, np.ndarray]:
    # clamp below Nyquist: a center frequency at/above sr/2 makes w0 >= pi,
    # which produces an unstable/aliased biquad regardless of gain or Q
    freq = min(freq, sr * 0.45)
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * q)
    cos_w0 = np.cos(w0)

    b0 = 1 + alpha * a
    b1 = -2 * cos_w0
    b2 = 1 - alpha * a
    a0 = 1 + alpha / a
    a1 = -2 * cos_w0
    a2 = 1 - alpha / a

    b = np.array([b0, b1, b2]) / a0
    a_coeffs = np.array([1.0, a1 / a0, a2 / a0])
    return b, a_coeffs


def eq3(y: np.ndarray, sr: int, params: dict[str, float]) -> np.ndarray:
    out = y.copy()
    for i in (1, 2, 3):
        freq = params[f"band{i}_freq"]
        gain_db = params[f"band{i}_gain_db"]
        q = params[f"band{i}_q"]
        if abs(gain_db) < 1e-6:
            continue
        b, a = _peaking_biquad(freq, gain_db, q, sr)
        out = lfilter(b, a, out)
    return out.astype(np.float32)


def compressor(y: np.ndarray, sr: int, params: dict[str, float]) -> np.ndarray:
    threshold_db = params["threshold_db"]
    ratio = params["ratio"]
    attack_ms = params["attack_ms"]
    release_ms = params["release_ms"]
    makeup_gain_db = params["makeup_gain_db"]

    attack_coeff = np.exp(-1.0 / (sr * attack_ms / 1000.0))
    release_coeff = np.exp(-1.0 / (sr * release_ms / 1000.0))

    abs_y = np.abs(y) + 1e-9
    env = np.zeros_like(abs_y)
    level = 0.0
    for i in range(len(abs_y)):
        coeff = attack_coeff if abs_y[i] > level else release_coeff
        level = coeff * level + (1 - coeff) * abs_y[i]
        env[i] = level

    env_db = 20 * np.log10(env + 1e-9)
    over_db = np.maximum(0.0, env_db - threshold_db)
    gain_reduction_db = -over_db * (1 - 1 / ratio)
    gain_lin = 10 ** ((gain_reduction_db + makeup_gain_db) / 20)
    return (y * gain_lin).astype(np.float32)


def saturation(y: np.ndarray, sr: int, params: dict[str, float]) -> np.ndarray:
    drive = params["drive"]
    mix = params["mix"]
    wet = np.tanh(y * drive) / np.tanh(drive)
    return ((1 - mix) * y + mix * wet).astype(np.float32)


def reverb(y: np.ndarray, sr: int, params: dict[str, float]) -> np.ndarray:
    room_size = params["room_size"]
    decay = params["decay"]
    wet_amt = params["wet"]
    if wet_amt < 1e-6:
        return y.astype(np.float32)

    comb_delays_ms = [29.7, 37.1, 41.1, 43.7]
    wet_signal = np.zeros_like(y, dtype=np.float32)
    for delay_ms in comb_delays_ms:
        d = max(1, int(sr * delay_ms / 1000.0 * (0.5 + room_size)))
        feedback = decay * 0.9
        b = np.zeros(d + 1, dtype=np.float32)
        b[0] = 1.0
        a = np.zeros(d + 1, dtype=np.float32)
        a[0] = 1.0
        a[d] = -feedback
        wet_signal += lfilter(b, a, y).astype(np.float32)
    wet_signal /= len(comb_delays_ms)

    allpass_delay = max(1, int(sr * 0.005))
    b_ap = np.zeros(allpass_delay + 1, dtype=np.float32)
    b_ap[0] = -0.7
    b_ap[allpass_delay] = 1.0
    a_ap = np.zeros(allpass_delay + 1, dtype=np.float32)
    a_ap[0] = 1.0
    a_ap[allpass_delay] = -0.7
    wet_signal = lfilter(b_ap, a_ap, wet_signal).astype(np.float32)

    return ((1 - wet_amt) * y + wet_amt * wet_signal).astype(np.float32)


DSP_DISPATCH = {
    "eq3": eq3,
    "compressor": compressor,
    "saturation": saturation,
    "reverb": reverb,
}
