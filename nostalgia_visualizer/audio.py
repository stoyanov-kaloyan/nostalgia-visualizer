from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np


@dataclass(slots=True)
class AudioFeatures:
    waveform: np.ndarray
    sample_rate: int
    duration_seconds: float
    frame_times: np.ndarray
    energy: np.ndarray
    onset: np.ndarray
    warmth: np.ndarray
    beat_pulse: np.ndarray


def analyze_audio(
    song_path: Path,
    fps: int,
    sample_rate: int,
    clip_seconds: float,
) -> AudioFeatures:
    if not song_path.exists():
        raise FileNotFoundError(
            f"Song not found: {song_path}. "
            "Add a song file at assets/song.mp3, set [audio].song_path in visualizer.toml, "
            "or pass --song /path/to/song."
        )

    waveform, active_sample_rate = librosa.load(song_path.as_posix(), sr=sample_rate, mono=True)
    if waveform.size == 0:
        raise ValueError(f"Song has no audio data: {song_path}")

    if clip_seconds > 0:
        max_samples = int(active_sample_rate * clip_seconds)
        waveform = waveform[:max_samples]
    duration_seconds = waveform.size / active_sample_rate
    frame_count = max(1, int(np.ceil(duration_seconds * fps)))
    frame_times = np.arange(frame_count, dtype=np.float32) / fps

    hop_length = 512
    rms = librosa.feature.rms(y=waveform, frame_length=2048, hop_length=hop_length)[0]
    onset_strength = librosa.onset.onset_strength(
        y=waveform, sr=active_sample_rate, hop_length=hop_length
    )
    centroid = librosa.feature.spectral_centroid(
        y=waveform, sr=active_sample_rate, hop_length=hop_length
    )[0]
    analysis_times = librosa.frames_to_time(
        np.arange(rms.size), sr=active_sample_rate, hop_length=hop_length
    )

    energy = _smooth(_normalize(_to_frame_curve(rms, analysis_times, frame_times)), 7)
    onset = _smooth(_normalize(_to_frame_curve(onset_strength, analysis_times, frame_times)), 5)
    warmth = 1.0 - _smooth(_normalize(_to_frame_curve(centroid, analysis_times, frame_times)), 9)

    _, beat_frames = librosa.beat.beat_track(
        y=waveform,
        sr=active_sample_rate,
        hop_length=hop_length,
        trim=False,
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=active_sample_rate, hop_length=hop_length)
    beat_pulse = _build_beat_pulse(frame_count=frame_count, beat_times=beat_times, fps=fps)

    return AudioFeatures(
        waveform=waveform.astype(np.float32, copy=False),
        sample_rate=active_sample_rate,
        duration_seconds=duration_seconds,
        frame_times=frame_times,
        energy=energy,
        onset=onset,
        warmth=warmth,
        beat_pulse=beat_pulse,
    )


def _to_frame_curve(
    source_values: np.ndarray,
    source_times: np.ndarray,
    frame_times: np.ndarray,
) -> np.ndarray:
    if source_values.size == 0:
        return np.zeros_like(frame_times, dtype=np.float32)
    return np.interp(
        frame_times,
        source_times,
        source_values,
        left=float(source_values[0]),
        right=float(source_values[-1]),
    ).astype(np.float32)


def _normalize(values: np.ndarray) -> np.ndarray:
    minimum = float(values.min())
    maximum = float(values.max())
    spread = maximum - minimum
    if spread < 1e-9:
        return np.zeros_like(values, dtype=np.float32)
    return ((values - minimum) / spread).astype(np.float32)


def _smooth(values: np.ndarray, window: int) -> np.ndarray:
    normalized_window = max(1, int(window))
    if normalized_window == 1:
        return values.astype(np.float32, copy=False)
    kernel = np.ones(normalized_window, dtype=np.float32) / normalized_window
    return np.convolve(values, kernel, mode="same").astype(np.float32)


def _build_beat_pulse(frame_count: int, beat_times: np.ndarray, fps: int) -> np.ndarray:
    pulse = np.zeros(frame_count, dtype=np.float32)
    spread = max(1, int(0.09 * fps))
    offsets = np.arange(-spread * 3, spread * 3 + 1, dtype=np.int32)
    weights = np.exp(-((offsets / spread) ** 2) / 2.0).astype(np.float32)

    for beat_time in beat_times:
        center = int(round(float(beat_time) * fps))
        start = max(0, center + offsets[0])
        end = min(frame_count, center + offsets[-1] + 1)
        if start >= end:
            continue
        weight_start = start - (center + offsets[0])
        weight_end = weight_start + (end - start)
        pulse[start:end] = np.maximum(pulse[start:end], weights[weight_start:weight_end])

    return pulse
