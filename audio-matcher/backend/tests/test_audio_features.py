import numpy as np
from scipy.signal import butter, lfilter

from app.services.audio_features import combined_distance, extract_features, feature_distance_breakdown

SR = 22050


def _white_noise(seed: int, seconds: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(int(SR * seconds)).astype(np.float32) * 0.3


def _lowpass(y: np.ndarray, cutoff_hz: float) -> np.ndarray:
    b, a = butter(4, cutoff_hz / (SR / 2), btype="low")
    return lfilter(b, a, y).astype(np.float32)


def _distance(y_ref: np.ndarray, y_cand: np.ndarray) -> float:
    ref_feat = extract_features(y_ref, SR)
    cand_feat = extract_features(y_cand, SR)
    breakdown = feature_distance_breakdown(ref_feat, cand_feat, y_ref, y_cand, SR)
    return combined_distance(breakdown)


def test_distance_is_monotonic_in_filter_cutoff_gap():
    """A candidate whose lowpass cutoff is closer to the reference's cutoff
    must score a smaller combined distance -- otherwise the metric would be
    useless as an optimizer objective (the optimizer would climb the wrong way)."""
    base = _white_noise(seed=1)
    reference = _lowpass(base, cutoff_hz=2000)

    close_match = _lowpass(base, cutoff_hz=2200)
    far_match = _lowpass(base, cutoff_hz=6000)

    d_close = _distance(reference, close_match)
    d_far = _distance(reference, far_match)

    assert d_close < d_far


def test_identical_signal_has_near_zero_distance():
    y = _lowpass(_white_noise(seed=2), cutoff_hz=3000)
    assert _distance(y, y.copy()) < 1e-6
