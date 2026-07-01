"""Audio feature extraction and perceptual-ish distance metric used both as the
optimizer objective and as the per-iteration progress signal shown to the user.
"""
from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np

FFT_SIZES = (512, 1024, 2048, 4096)


@dataclass
class AudioFeatures:
    log_mel_mean: np.ndarray
    mfcc_mean: np.ndarray
    spectral_centroid: float
    spectral_bandwidth: float
    spectral_flux: float
    rms: float
    crest_factor: float


def extract_features(y: np.ndarray, sr: int) -> AudioFeatures:
    if y.ndim > 1:
        y = librosa.to_mono(y)
    y = y.astype(np.float32)
    if np.max(np.abs(y)) < 1e-9:
        y = y + 1e-9

    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=40)
    log_mel = librosa.power_to_db(mel)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    rms = librosa.feature.rms(y=y)

    peak = float(np.max(np.abs(y)))
    rms_val = float(np.sqrt(np.mean(y**2)) + 1e-12)

    return AudioFeatures(
        log_mel_mean=np.mean(log_mel, axis=1),
        mfcc_mean=np.mean(mfcc, axis=1),
        spectral_centroid=float(np.mean(centroid)),
        spectral_bandwidth=float(np.mean(bandwidth)),
        spectral_flux=float(np.mean(onset_env)),
        rms=float(np.mean(rms)),
        crest_factor=peak / rms_val,
    )


def multi_resolution_stft_distance(y_ref: np.ndarray, y_cand: np.ndarray, sr: int) -> float:
    if y_ref.ndim > 1:
        y_ref = librosa.to_mono(y_ref)
    if y_cand.ndim > 1:
        y_cand = librosa.to_mono(y_cand)
    n = min(len(y_ref), len(y_cand))
    y_ref, y_cand = y_ref[:n], y_cand[:n]

    total = 0.0
    for n_fft in FFT_SIZES:
        hop = n_fft // 4
        s_ref = np.abs(librosa.stft(y_ref, n_fft=n_fft, hop_length=hop))
        s_cand = np.abs(librosa.stft(y_cand, n_fft=n_fft, hop_length=hop))
        m = min(s_ref.shape[1], s_cand.shape[1])
        s_ref, s_cand = s_ref[:, :m], s_cand[:, :m]
        log_ref = np.log(s_ref + 1e-7)
        log_cand = np.log(s_cand + 1e-7)
        total += float(np.mean(np.abs(log_ref - log_cand)))
    return total / len(FFT_SIZES)


def feature_distance_breakdown(
    ref: AudioFeatures, cand: AudioFeatures, y_ref: np.ndarray, y_cand: np.ndarray, sr: int
) -> dict[str, float]:
    return {
        "spectral_stft": multi_resolution_stft_distance(y_ref, y_cand, sr),
        "log_mel": float(np.mean(np.abs(ref.log_mel_mean - cand.log_mel_mean))),
        "mfcc": float(np.mean(np.abs(ref.mfcc_mean - cand.mfcc_mean))),
        "spectral_centroid": abs(ref.spectral_centroid - cand.spectral_centroid) / (ref.spectral_centroid + 1e-6),
        "spectral_bandwidth": abs(ref.spectral_bandwidth - cand.spectral_bandwidth) / (ref.spectral_bandwidth + 1e-6),
        "spectral_flux": abs(ref.spectral_flux - cand.spectral_flux) / (ref.spectral_flux + 1e-6),
        "loudness": abs(ref.rms - cand.rms) / (ref.rms + 1e-6),
        "crest_factor": abs(ref.crest_factor - cand.crest_factor) / (ref.crest_factor + 1e-6),
    }


DEFAULT_WEIGHTS = {
    "spectral_stft": 1.0,
    "log_mel": 0.5,
    "mfcc": 0.3,
    "spectral_centroid": 0.4,
    "spectral_bandwidth": 0.3,
    "spectral_flux": 0.3,
    "loudness": 0.6,
    "crest_factor": 0.4,
}


def combined_distance(breakdown: dict[str, float], weights: dict[str, float] | None = None) -> float:
    weights = weights or DEFAULT_WEIGHTS
    return sum(weights.get(k, 0.0) * v for k, v in breakdown.items())
