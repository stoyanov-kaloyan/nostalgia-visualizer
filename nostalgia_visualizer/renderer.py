from __future__ import annotations

from pathlib import Path
import subprocess

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from tqdm import tqdm

from .audio import AudioFeatures
from .config import VisualizerConfig
from .presets import Theme

_EFFECT_NAMES: tuple[str, ...] = (
    "glitch_bands",
    "chroma_echo",
    "scan_fall",
    "pixel_mosaic",
    "tear_lines",
)


def available_effect_names() -> list[str]:
    return list(_EFFECT_NAMES)


def render_visualizer_video(
    config: VisualizerConfig,
    theme: Theme,
    features: AudioFeatures,
) -> Path:
    output_path = config.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_video = output_path.with_name(f"{output_path.stem}.video-only.mp4")

    selected_effects = _normalize_effect_names(config.effect_names)
    effect_schedule = _build_effect_schedule(
        config=config,
        features=features,
        effect_count=len(selected_effects),
    )

    frame_renderer = FrameRenderer(config=config, theme=theme)
    writer = imageio.get_writer(
        temp_video.as_posix(),
        fps=config.fps,
        codec="libx264",
        macro_block_size=None,
        ffmpeg_log_level="error",
    )
    progress = None
    try:
        frame_total = features.frame_times.size
        progress = tqdm(
            total=frame_total,
            desc="Rendering frames",
            unit="frame",
            dynamic_ncols=True,
            leave=True,
        )
        for frame_index in range(frame_total):
            effect_name = selected_effects[int(effect_schedule[frame_index])]
            frame = frame_renderer.render_frame(
                frame_index=frame_index,
                features=features,
                effect_name=effect_name,
            )
            writer.append_data(frame)
            progress.update(1)
    finally:
        if progress is not None:
            progress.close()
        writer.close()

    _mux_audio(video_path=temp_video, audio_path=config.song_path, output_path=output_path)
    temp_video.unlink(missing_ok=True)
    return output_path


class FrameRenderer:
    def __init__(self, config: VisualizerConfig, theme: Theme):
        self.width = config.width
        self.height = config.height
        self.fps = config.fps
        self.theme = theme
        self.master_seed = config.seed

        self.palette = np.array(theme.palette, dtype=np.uint8)
        self.base_background = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.base_background[:] = np.array(theme.background_color, dtype=np.uint8)

        self.scanline_mask = np.ones((self.height, 1, 1), dtype=np.float32)
        self.scanline_mask[1::2, 0, 0] = max(0.0, 1.0 - self.theme.scanline_strength)

    def render_frame(
        self,
        frame_index: int,
        features: AudioFeatures,
        effect_name: str,
    ) -> np.ndarray:
        energy = float(features.energy[frame_index])
        onset = float(features.onset[frame_index])
        beat = float(features.beat_pulse[frame_index])
        rng = np.random.default_rng(self.master_seed + frame_index * 104_729 + 17)

        frame = self.base_background.copy()
        self._apply_effect(
            frame=frame,
            effect_name=effect_name,
            rng=rng,
            frame_index=frame_index,
            energy=energy,
            onset=onset,
            beat=beat,
        )
        frame = self._apply_channel_split(frame, rng, onset, beat)
        frame = self._apply_scanlines(frame)
        frame = self._apply_noise(frame, rng, energy, beat)
        return self._apply_strobe(frame, rng, beat, onset)

    def _apply_effect(
        self,
        frame: np.ndarray,
        effect_name: str,
        rng: np.random.Generator,
        frame_index: int,
        energy: float,
        onset: float,
        beat: float,
    ) -> None:
        if effect_name == "glitch_bands":
            self._draw_glitch_bands(frame, rng, energy, onset, beat, intensity=1.0)
            self._draw_sporadic_blocks(frame, rng, energy, onset, beat, intensity=1.0)
            self._draw_sparks(frame, rng, onset, beat, intensity=1.0)
            return

        if effect_name == "chroma_echo":
            self._draw_echo_sweeps(frame, rng, frame_index, energy, onset, beat)
            self._draw_glitch_bands(frame, rng, energy, onset, beat, intensity=0.75)
            self._draw_sparks(frame, rng, onset, beat, intensity=1.4)
            return

        if effect_name == "scan_fall":
            self._draw_vertical_fall(frame, rng, frame_index, energy, onset, beat)
            self._draw_tear_lines(frame, rng, onset, beat, intensity=0.85)
            self._draw_sparks(frame, rng, onset, beat, intensity=0.9)
            return

        if effect_name == "pixel_mosaic":
            self._draw_mosaic_blocks(frame, rng, energy, onset, beat)
            self._draw_sporadic_blocks(frame, rng, energy, onset, beat, intensity=0.65)
            self._draw_sparks(frame, rng, onset, beat, intensity=1.2)
            return

        if effect_name == "tear_lines":
            self._draw_tear_lines(frame, rng, onset, beat, intensity=1.25)
            self._draw_glitch_bands(frame, rng, energy, onset, beat, intensity=0.9)
            self._draw_sparks(frame, rng, onset, beat, intensity=1.0)
            return

        raise ValueError(f"Unknown effect '{effect_name}'.")

    def _pick_color(self, rng: np.random.Generator, intensity_scale: float = 1.0) -> np.ndarray:
        base = self.palette[int(rng.integers(0, len(self.palette)))]
        gain = (0.55 + rng.random() * 0.65) * intensity_scale
        scaled = np.clip(base.astype(np.float32) * gain, 0, 255)
        return scaled.astype(np.uint8)

    def _draw_glitch_bands(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        energy: float,
        onset: float,
        beat: float,
        intensity: float,
    ) -> None:
        normalized_intensity = max(0.2, intensity)
        max_band_height = max(3, int(self.height * (0.01 + 0.05 * beat)))
        band_count = 7 + int((energy + onset) * 22 * self.theme.glitch_intensity * normalized_intensity)
        max_shift = int(
            6 + (onset * 70 + beat * 90) * self.theme.glitch_intensity * normalized_intensity
        )

        for _ in range(band_count):
            band_height = int(rng.integers(1, max_band_height + 1))
            y = int(rng.integers(0, max(1, self.height - band_height + 1)))
            color = self._pick_color(
                rng, intensity_scale=(0.7 + energy * 0.9) * normalized_intensity
            )

            section = frame[y : y + band_height, :, :]
            section[:] = np.maximum(section, color)
            if max_shift > 0 and rng.random() < 0.78:
                shift = int(rng.integers(-max_shift, max_shift + 1))
                section[:] = np.roll(section, shift, axis=1)

    def _draw_sporadic_blocks(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        energy: float,
        onset: float,
        beat: float,
        intensity: float,
    ) -> None:
        normalized_intensity = max(0.2, intensity)
        block_count = 4 + int(
            (onset * 18 + beat * 10) * self.theme.glitch_intensity * normalized_intensity
        )
        max_width = max(8, int(self.width * 0.11))
        max_height = max(6, int(self.height * 0.16))

        for _ in range(block_count):
            block_w = int(rng.integers(6, max_width + 1))
            block_h = int(rng.integers(4, max_height + 1))
            x = int(rng.integers(0, max(1, self.width - block_w + 1)))
            y = int(rng.integers(0, max(1, self.height - block_h + 1)))
            color = self._pick_color(
                rng,
                intensity_scale=(0.9 + onset + beat * 0.6) * normalized_intensity,
            )

            section = frame[y : y + block_h, x : x + block_w, :]
            section[:] = np.maximum(section, color)

            if rng.random() < 0.42:
                line_y = y + int(rng.integers(0, block_h))
                frame[line_y : line_y + 1, x : x + block_w, :] = 0

        line_count = 4 + int(
            (energy + beat) * 22 * self.theme.glitch_intensity * normalized_intensity
        )
        for _ in range(line_count):
            x = int(rng.integers(0, self.width))
            thickness = int(rng.integers(1, 4))
            color = self._pick_color(rng, intensity_scale=(0.75 + beat) * normalized_intensity)
            frame[:, x : x + thickness, :] = np.maximum(frame[:, x : x + thickness, :], color)

    def _draw_sparks(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        onset: float,
        beat: float,
        intensity: float,
    ) -> None:
        normalized_intensity = max(0.2, intensity)
        density = normalized_intensity * (0.00003 + onset * 0.00022 + beat * 0.00012)
        spark_count = int(self.width * self.height * density)
        if spark_count <= 0:
            return

        xs = rng.integers(0, self.width, size=spark_count)
        ys = rng.integers(0, self.height, size=spark_count)
        color_ids = rng.integers(0, len(self.palette), size=spark_count)
        spark_colors = self.palette[color_ids]
        frame[ys, xs] = np.maximum(frame[ys, xs], spark_colors)

        chunky_count = spark_count // 6
        if chunky_count <= 0:
            return
        xs2 = rng.integers(0, max(1, self.width - 2), size=chunky_count)
        ys2 = rng.integers(0, max(1, self.height - 2), size=chunky_count)
        color_ids2 = rng.integers(0, len(self.palette), size=chunky_count)
        for x, y, color_id in zip(xs2, ys2, color_ids2):
            frame[y : y + 2, x : x + 2, :] = np.maximum(
                frame[y : y + 2, x : x + 2, :],
                self.palette[int(color_id)],
            )

    def _draw_echo_sweeps(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        frame_index: int,
        energy: float,
        onset: float,
        beat: float,
    ) -> None:
        sweep_count = 3 + int((onset + beat) * 9 * self.theme.glitch_intensity)
        max_h = max(8, int(self.height * 0.18))
        max_shift = int(8 + (onset * 80 + beat * 110))

        for _ in range(sweep_count):
            height = int(rng.integers(4, max_h + 1))
            y = int(rng.integers(0, max(1, self.height - height + 1)))
            color = self._pick_color(rng, intensity_scale=0.65 + energy + beat * 0.9)
            section = frame[y : y + height, :, :]
            section[:] = np.maximum(section, color)

            shift = int(rng.integers(-max_shift, max_shift + 1))
            section[:] = np.roll(section, shift + frame_index % 7, axis=1)

            if rng.random() < 0.65:
                hole_count = int(rng.integers(1, 5))
                for _ in range(hole_count):
                    hole_w = int(rng.integers(8, max(9, int(self.width * 0.07))))
                    hole_x = int(rng.integers(0, max(1, self.width - hole_w + 1)))
                    section[:, hole_x : hole_x + hole_w, :] = 0

    def _draw_vertical_fall(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        frame_index: int,
        energy: float,
        onset: float,
        beat: float,
    ) -> None:
        line_count = 14 + int((energy + onset + beat) * 70 * self.theme.glitch_intensity)
        max_len = max(8, int(self.height * 0.34))

        for _ in range(line_count):
            x = int(rng.integers(0, self.width))
            thickness = int(rng.integers(1, 3))
            speed = int(rng.integers(2, 12))
            line_len = int(rng.integers(6, max_len + 1))
            offset = int(rng.integers(0, self.height + line_len))

            head = (frame_index * speed + offset) % (self.height + line_len) - line_len
            y_start = max(0, head)
            y_end = min(self.height, head + line_len)
            if y_start >= y_end:
                continue

            color = self._pick_color(rng, intensity_scale=0.75 + onset + beat * 0.7)
            frame[y_start:y_end, x : x + thickness, :] = np.maximum(
                frame[y_start:y_end, x : x + thickness, :], color
            )

    def _draw_mosaic_blocks(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        energy: float,
        onset: float,
        beat: float,
    ) -> None:
        cell_size = max(6, int(14 - min(7, beat * 8)))
        grid_w = max(1, self.width // cell_size)
        grid_h = max(1, self.height // cell_size)
        density = 0.09 + onset * 0.33 + beat * 0.18
        active = int(grid_w * grid_h * density)

        for _ in range(active):
            cell_x = int(rng.integers(0, grid_w))
            cell_y = int(rng.integers(0, grid_h))
            x0 = cell_x * cell_size
            y0 = cell_y * cell_size
            x1 = min(self.width, x0 + cell_size)
            y1 = min(self.height, y0 + cell_size)
            color = self._pick_color(rng, intensity_scale=0.8 + energy + onset * 0.7)
            frame[y0:y1, x0:x1, :] = np.maximum(frame[y0:y1, x0:x1, :], color)

    def _draw_tear_lines(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        onset: float,
        beat: float,
        intensity: float,
    ) -> None:
        normalized_intensity = max(0.2, intensity)
        line_count = 8 + int((onset + beat) * 40 * self.theme.glitch_intensity * normalized_intensity)
        max_shift = int(8 + (onset * 95 + beat * 130) * normalized_intensity)

        for _ in range(line_count):
            y = int(rng.integers(0, self.height))
            thickness = int(rng.integers(1, 5))
            y_end = min(self.height, y + thickness)

            shift = int(rng.integers(-max_shift, max_shift + 1))
            frame[y:y_end, :, :] = np.roll(frame[y:y_end, :, :], shift, axis=1)

            if rng.random() < 0.58:
                streak_w = int(rng.integers(6, max(7, int(self.width * 0.12))))
                streak_x = int(rng.integers(0, max(1, self.width - streak_w + 1)))
                color = self._pick_color(rng, intensity_scale=0.75 + beat)
                frame[y:y_end, streak_x : streak_x + streak_w, :] = np.maximum(
                    frame[y:y_end, streak_x : streak_x + streak_w, :], color
                )

    def _apply_channel_split(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        onset: float,
        beat: float,
    ) -> np.ndarray:
        shift = int((1 + onset * 5 + beat * 8) * self.theme.glitch_intensity)
        if shift <= 0:
            return frame

        glitched = frame.copy()
        glitched[:, :, 0] = np.roll(frame[:, :, 0], shift, axis=1)
        glitched[:, :, 2] = np.roll(frame[:, :, 2], -shift, axis=1)

        if rng.random() < 0.65:
            band_h = int(rng.integers(2, max(3, int(self.height * 0.08))))
            y = int(rng.integers(0, max(1, self.height - band_h + 1)))
            band_shift = int(rng.integers(-shift * 4, shift * 4 + 1))
            glitched[y : y + band_h, :, :] = np.roll(
                glitched[y : y + band_h, :, :], band_shift, axis=1
            )
        return glitched

    def _apply_scanlines(self, frame: np.ndarray) -> np.ndarray:
        shaded = frame.astype(np.float32)
        shaded *= self.scanline_mask
        return np.clip(shaded, 0, 255).astype(np.uint8)

    def _apply_noise(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        energy: float,
        beat: float,
    ) -> np.ndarray:
        amplitude = int(8 + (energy * 26 + beat * 18) * self.theme.grain_strength)
        if amplitude <= 0:
            return frame
        noise = rng.integers(
            -amplitude,
            amplitude + 1,
            size=(self.height, self.width, 1),
            dtype=np.int16,
        )
        frame_int = frame.astype(np.int16)
        frame_int += noise
        return np.clip(frame_int, 0, 255).astype(np.uint8)

    def _apply_strobe(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        beat: float,
        onset: float,
    ) -> np.ndarray:
        trigger = beat * 0.7 + onset * 0.9
        if trigger < 0.25 or rng.random() > min(0.9, trigger):
            return frame

        flash_color = self._pick_color(rng, intensity_scale=1.1 + trigger * 0.5).astype(np.float32)
        flash_overlay = flash_color.reshape(1, 1, 3) * (0.10 + 0.20 * trigger)

        flashed = frame.astype(np.float32)
        if rng.random() < 0.5:
            band_h = int(rng.integers(6, max(7, int(self.height * 0.15))))
            y = int(rng.integers(0, max(1, self.height - band_h + 1)))
            flashed[y : y + band_h, :, :] += flash_overlay * 2.8
        else:
            flashed += flash_overlay
        return np.clip(flashed, 0, 255).astype(np.uint8)


def _normalize_effect_names(effect_names: tuple[str, ...]) -> tuple[str, ...]:
    if not effect_names:
        raise ValueError("effect_names cannot be empty.")

    available = set(_EFFECT_NAMES)
    unique: list[str] = []
    for name in effect_names:
        normalized = name.strip()
        if not normalized:
            continue
        if normalized not in available:
            names = ", ".join(_EFFECT_NAMES)
            raise ValueError(f"Unknown effect '{normalized}'. Choose one of: {names}")
        if normalized not in unique:
            unique.append(normalized)

    if not unique:
        raise ValueError("effect_names cannot be empty.")
    return tuple(unique)


def _build_effect_schedule(
    config: VisualizerConfig,
    features: AudioFeatures,
    effect_count: int,
) -> np.ndarray:
    frame_total = features.frame_times.size
    if frame_total <= 0:
        return np.array([], dtype=np.int16)

    beats_per_swap = max(1, config.swap_every_bars * config.beats_per_bar)
    change_frames = _bar_change_frames(
        beat_frame_indices=features.beat_frame_indices,
        beats_per_swap=beats_per_swap,
        frame_total=frame_total,
    )
    if change_frames.size == 0:
        fallback_interval = _fallback_swap_interval_frames(config=config, features=features)
        change_frames = np.arange(
            fallback_interval, frame_total, fallback_interval, dtype=np.int32
        )

    schedule = np.empty(frame_total, dtype=np.int16)
    start = 0
    effect_index = 0
    for change_frame in change_frames:
        if change_frame <= start:
            continue
        schedule[start:change_frame] = effect_index % effect_count
        start = int(change_frame)
        effect_index += 1
    schedule[start:frame_total] = effect_index % effect_count
    return schedule


def _bar_change_frames(
    beat_frame_indices: np.ndarray,
    beats_per_swap: int,
    frame_total: int,
) -> np.ndarray:
    if beat_frame_indices.size == 0:
        return np.array([], dtype=np.int32)

    marks = beat_frame_indices[beats_per_swap::beats_per_swap].astype(np.int32, copy=False)
    marks = marks[(marks > 0) & (marks < frame_total)]
    return np.unique(marks)


def _fallback_swap_interval_frames(config: VisualizerConfig, features: AudioFeatures) -> int:
    if features.tempo_bpm > 0:
        beat_seconds = 60.0 / features.tempo_bpm
        bar_seconds = beat_seconds * max(1, config.beats_per_bar)
        interval_seconds = bar_seconds * max(1, config.swap_every_bars)
    else:
        interval_seconds = 2.0 * max(1, config.swap_every_bars)
    return max(1, int(round(interval_seconds * config.fps)))


def _mux_audio(video_path: Path, audio_path: Path, output_path: Path) -> None:
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        video_path.as_posix(),
        "-i",
        audio_path.as_posix(),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-shortest",
        output_path.as_posix(),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error_output = result.stderr.strip() or "Unknown ffmpeg error."
        raise RuntimeError(f"Failed to mux audio and video: {error_output}")
