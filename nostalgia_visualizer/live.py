from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import os
import time
from typing import Any

import numpy as np

from .config import VisualizerConfig
from .presets import get_theme
from .renderer import FrameRenderer, normalize_effect_names


@dataclass(slots=True)
class LiveFrameMetrics:
    energy: float
    onset: float
    beat: float
    beat_triggered: bool


class LiveAudioAnalyzer:
    def __init__(
        self,
        sample_rate: int,
        input_device: str | int | None,
        block_size: int = 1024,
    ):
        self.sample_rate = sample_rate
        self.input_device = input_device
        self.block_size = block_size

        self._lock = Lock()
        self._stream: Any | None = None
        self._status_message: str | None = None

        self._energy = 0.0
        self._onset = 0.0
        self._beat = 0.0
        self._beat_triggered = False

        self._noise_floor = 0.0005
        self._peak_level = 0.02
        self._previous_rms = 0.0
        self._last_beat_time = 0.0

    def start(self) -> None:
        sounddevice = _import_sounddevice()
        self._stream = sounddevice.InputStream(
            samplerate=self.sample_rate,
            device=self.input_device,
            channels=1,
            blocksize=self.block_size,
            dtype="float32",
            callback=self._on_audio,
        )
        self._stream.start()

    def stop(self) -> None:
        stream = self._stream
        if stream is None:
            return
        try:
            stream.stop()
        finally:
            stream.close()
            self._stream = None

    def __enter__(self) -> "LiveAudioAnalyzer":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.stop()

    def snapshot(self) -> tuple[LiveFrameMetrics, str | None]:
        with self._lock:
            metrics = LiveFrameMetrics(
                energy=self._energy,
                onset=self._onset,
                beat=self._beat,
                beat_triggered=self._beat_triggered,
            )
            self._beat_triggered = False
            status_message = self._status_message
            self._status_message = None
        return metrics, status_message

    def _on_audio(self, indata: np.ndarray, frames: int, time_info: dict[str, float], status: Any) -> None:
        del frames, time_info
        if status:
            with self._lock:
                self._status_message = str(status)

        mono = np.asarray(indata[:, 0], dtype=np.float32)
        rms = float(np.sqrt(np.mean(mono * mono) + 1e-12))

        with self._lock:
            self._noise_floor = 0.995 * self._noise_floor + 0.005 * rms
            self._peak_level = max(self._peak_level * 0.995, rms)

            level_span = max(1e-6, self._peak_level - self._noise_floor)
            energy_raw = (rms - self._noise_floor) / level_span
            energy_norm = float(np.clip(energy_raw, 0.0, 1.0))

            delta = max(0.0, rms - self._previous_rms)
            onset_raw = delta / (self._peak_level + 1e-6) * 6.0
            onset_norm = float(np.clip(onset_raw, 0.0, 1.0))

            self._energy = 0.80 * self._energy + 0.20 * energy_norm
            self._onset = 0.75 * self._onset + 0.25 * onset_norm

            beat_now = False
            now = time.monotonic()
            if self._energy > 0.20 and self._onset > 0.46 and (now - self._last_beat_time) >= 0.18:
                beat_now = True
                self._last_beat_time = now
                self._beat = 1.0
            else:
                self._beat = max(0.0, self._beat * 0.90)

            if beat_now:
                self._beat_triggered = True

            self._previous_rms = rms


def run_live_visualizer(
    config: VisualizerConfig,
    *,
    input_device: str | int | None = None,
    fullscreen: bool = False,
) -> None:
    _validate_live_config(config)
    pygame = _import_pygame()
    selected_effects = normalize_effect_names(config.effect_names)
    beats_per_swap = max(1, config.swap_every_bars * config.beats_per_bar)

    device = config.live_input_device if input_device is None else input_device
    theme = get_theme(config.theme)
    renderer = FrameRenderer(config=config, theme=theme)

    pygame.init()
    try:
        flags = pygame.FULLSCREEN if fullscreen else 0
        screen = pygame.display.set_mode((config.width, config.height), flags)
        pygame.display.set_caption("Nostalgia Visualizer Live")
        clock = pygame.time.Clock()

        frame_index = 0
        effect_index = 0
        beat_counter = 0
        status_text = ""

        with LiveAudioAnalyzer(sample_rate=config.sample_rate, input_device=device) as analyzer:
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_ESCAPE, pygame.K_q):
                            running = False
                        elif event.key == pygame.K_SPACE:
                            effect_index = (effect_index + 1) % len(selected_effects)
                            beat_counter = 0

                metrics, latest_status = analyzer.snapshot()
                if latest_status:
                    status_text = latest_status

                if metrics.beat_triggered and len(selected_effects) > 1:
                    beat_counter += 1
                    if beat_counter >= beats_per_swap:
                        beat_counter = 0
                        effect_index = (effect_index + 1) % len(selected_effects)

                effect_name = selected_effects[effect_index]
                frame = renderer.render_frame_from_values(
                    frame_index=frame_index,
                    effect_name=effect_name,
                    energy=metrics.energy,
                    onset=metrics.onset,
                    beat=metrics.beat,
                )
                surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
                screen.blit(surface, (0, 0))
                pygame.display.flip()

                if frame_index % max(1, config.fps) == 0:
                    caption = (
                        f"Nostalgia Visualizer Live | effect={effect_name} "
                        f"| energy={metrics.energy:.2f} onset={metrics.onset:.2f}"
                    )
                    if status_text:
                        caption = f"{caption} | audio-status={status_text}"
                    pygame.display.set_caption(caption)

                frame_index += 1
                clock.tick(config.fps)
    finally:
        pygame.quit()


def list_input_devices() -> list[str]:
    sounddevice = _import_sounddevice()
    devices = sounddevice.query_devices()
    host_apis = sounddevice.query_hostapis()
    default_input = _default_input_device_index(sounddevice)

    rows: list[str] = []
    for index, device in enumerate(devices):
        max_input_channels = int(device.get("max_input_channels", 0))
        if max_input_channels <= 0:
            continue
        host_api_index = int(device.get("hostapi", 0))
        host_name = str(host_apis[host_api_index]["name"])
        marker = "*" if default_input == index else " "
        name = str(device.get("name", f"Input {index}"))
        rows.append(f"{marker} {index}: {name} [{host_name}]")

    if not rows:
        return ["No input-capable audio devices were found."]
    return rows


def _default_input_device_index(sounddevice: Any) -> int | None:
    default_device = getattr(sounddevice.default, "device", None)
    if default_device is None:
        return None

    candidate: Any = None
    if hasattr(default_device, "input"):
        candidate = getattr(default_device, "input")
    elif isinstance(default_device, (tuple, list)):
        if default_device:
            candidate = default_device[0]
    else:
        try:
            candidate = default_device[0]
        except Exception:
            candidate = default_device

    try:
        index = int(candidate)
    except (TypeError, ValueError):
        return None
    if index < 0:
        return None
    return index


def _import_sounddevice() -> Any:
    try:
        import sounddevice  # type: ignore
    except ImportError as error:
        raise RuntimeError(
            "Live mode requires the 'sounddevice' dependency. "
            "Install dependencies with `uv sync`."
        ) from error
    except OSError as error:
        raise RuntimeError(
            "Live mode requires the PortAudio runtime. "
            "On Ubuntu/Debian install it with `sudo apt install libportaudio2`."
        ) from error
    return sounddevice


def _import_pygame() -> Any:
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame  # type: ignore
    except ImportError as error:
        raise RuntimeError(
            "Live mode requires the 'pygame' dependency. "
            "Install dependencies with `uv sync`."
        ) from error
    return pygame


def _validate_live_config(config: VisualizerConfig) -> None:
    if config.fps <= 0:
        raise ValueError("fps must be greater than 0")
    if config.width <= 0 or config.height <= 0:
        raise ValueError("width and height must be greater than 0")
    if config.sample_rate <= 0:
        raise ValueError("sample_rate must be greater than 0")
    if config.swap_every_bars <= 0:
        raise ValueError("swap_every_bars must be greater than 0")
    if config.beats_per_bar <= 0:
        raise ValueError("beats_per_bar must be greater than 0")
