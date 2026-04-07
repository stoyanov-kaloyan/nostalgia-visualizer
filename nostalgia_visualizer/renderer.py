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

    def render_frame(self, frame_index: int, features: AudioFeatures) -> np.ndarray:
        energy = float(features.energy[frame_index])
        onset = float(features.onset[frame_index])
        beat = float(features.beat_pulse[frame_index])
        rng = np.random.default_rng(self.master_seed + frame_index * 104_729 + 17)

        frame = self.base_background.copy()
        self._draw_glitch_bands(frame, rng, energy, onset, beat)
        self._draw_sporadic_blocks(frame, rng, energy, onset, beat)
        self._draw_sparks(frame, rng, onset, beat)

        frame = self._apply_channel_split(frame, rng, onset, beat)
        frame = self._apply_scanlines(frame)
        frame = self._apply_noise(frame, rng, energy, beat)
        return self._apply_strobe(frame, rng, beat, onset)

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
    ) -> None:
        max_band_height = max(3, int(self.height * (0.01 + 0.05 * beat)))
        band_count = 7 + int((energy + onset) * 22 * self.theme.glitch_intensity)
        max_shift = int(6 + (onset * 70 + beat * 90) * self.theme.glitch_intensity)

        for _ in range(band_count):
            band_height = int(rng.integers(1, max_band_height + 1))
            y = int(rng.integers(0, max(1, self.height - band_height + 1)))
            color = self._pick_color(rng, intensity_scale=0.7 + energy * 0.9)

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
    ) -> None:
        block_count = 4 + int((onset * 18 + beat * 10) * self.theme.glitch_intensity)
        max_width = max(8, int(self.width * 0.11))
        max_height = max(6, int(self.height * 0.16))

        for _ in range(block_count):
            block_w = int(rng.integers(6, max_width + 1))
            block_h = int(rng.integers(4, max_height + 1))
            x = int(rng.integers(0, max(1, self.width - block_w + 1)))
            y = int(rng.integers(0, max(1, self.height - block_h + 1)))
            color = self._pick_color(rng, intensity_scale=0.9 + onset + beat * 0.6)

            section = frame[y : y + block_h, x : x + block_w, :]
            section[:] = np.maximum(section, color)

            if rng.random() < 0.42:
                line_y = y + int(rng.integers(0, block_h))
                frame[line_y : line_y + 1, x : x + block_w, :] = 0

        line_count = 5 + int((energy + beat) * 24 * self.theme.glitch_intensity)
        for _ in range(line_count):
            x = int(rng.integers(0, self.width))
            thickness = int(rng.integers(1, 4))
            color = self._pick_color(rng, intensity_scale=0.8 + beat)
            frame[:, x : x + thickness, :] = np.maximum(frame[:, x : x + thickness, :], color)

    def _draw_sparks(
        self,
        frame: np.ndarray,
        rng: np.random.Generator,
        onset: float,
        beat: float,
    ) -> None:
        density = 0.00003 + (onset * 0.00022) + (beat * 0.00012)
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


def render_visualizer_video(
    config: VisualizerConfig,
    theme: Theme,
    features: AudioFeatures,
) -> Path:
    output_path = config.output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_video = output_path.with_name(f"{output_path.stem}.video-only.mp4")

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
        for index in range(frame_total):
            writer.append_data(frame_renderer.render_frame(index, features))
            progress.update(1)
    finally:
        if progress is not None:
            progress.close()
        writer.close()

    _mux_audio(video_path=temp_video, audio_path=config.song_path, output_path=output_path)
    temp_video.unlink(missing_ok=True)
    return output_path


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
