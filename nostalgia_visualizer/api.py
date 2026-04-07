from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Sequence

from .config import VisualizerConfig, load_config
from .pipeline import run_visualizer


def render_song(
    song_path: str | Path,
    output_path: str | Path = Path("renders/output.mp4"),
    *,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    sample_rate: int = 44_100,
    clip_seconds: float = 30.0,
    theme: str = "blackout_glitch",
    effect_names: Sequence[str] = ("glitch_bands", "chroma_echo", "scan_fall"),
    swap_every_bars: int = 2,
    beats_per_bar: int = 4,
    seed: int = 7,
) -> Path:
    config = VisualizerConfig(
        song_path=_to_path(song_path),
        output_path=_to_path(output_path),
        width=width,
        height=height,
        fps=fps,
        sample_rate=sample_rate,
        clip_seconds=clip_seconds,
        theme=theme,
        effect_names=tuple(effect_names),
        swap_every_bars=swap_every_bars,
        beats_per_bar=beats_per_bar,
        seed=seed,
    )
    return run_visualizer(config)


def render_from_config(
    config_path: str | Path | None = None,
    *,
    song_path: str | Path | None = None,
    output_path: str | Path | None = None,
    theme: str | None = None,
    effect_names: Sequence[str] | None = None,
    swap_every_bars: int | None = None,
    beats_per_bar: int | None = None,
    clip_seconds: float | None = None,
    fps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    sample_rate: int | None = None,
    seed: int | None = None,
) -> Path:
    resolved_config_path = None if config_path is None else _to_path(config_path)
    config = load_config(resolved_config_path)
    return render_with_config(
        config,
        song_path=song_path,
        output_path=output_path,
        theme=theme,
        effect_names=effect_names,
        swap_every_bars=swap_every_bars,
        beats_per_bar=beats_per_bar,
        clip_seconds=clip_seconds,
        fps=fps,
        width=width,
        height=height,
        sample_rate=sample_rate,
        seed=seed,
    )


def render_with_config(
    config: VisualizerConfig,
    *,
    song_path: str | Path | None = None,
    output_path: str | Path | None = None,
    theme: str | None = None,
    effect_names: Sequence[str] | None = None,
    swap_every_bars: int | None = None,
    beats_per_bar: int | None = None,
    clip_seconds: float | None = None,
    fps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    sample_rate: int | None = None,
    seed: int | None = None,
) -> Path:
    updated = replace(config)

    if song_path is not None:
        updated.song_path = _to_path(song_path)
    if output_path is not None:
        updated.output_path = _to_path(output_path)
    if theme is not None:
        updated.theme = theme
    if effect_names is not None:
        updated.effect_names = tuple(effect_names)
    if swap_every_bars is not None:
        updated.swap_every_bars = swap_every_bars
    if beats_per_bar is not None:
        updated.beats_per_bar = beats_per_bar
    if clip_seconds is not None:
        updated.clip_seconds = clip_seconds
    if fps is not None:
        updated.fps = fps
    if width is not None:
        updated.width = width
    if height is not None:
        updated.height = height
    if sample_rate is not None:
        updated.sample_rate = sample_rate
    if seed is not None:
        updated.seed = seed

    return run_visualizer(updated)


def _to_path(value: str | Path) -> Path:
    if isinstance(value, Path):
        return value
    return Path(value)
