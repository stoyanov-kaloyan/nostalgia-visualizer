from __future__ import annotations

from pathlib import Path

from .audio import analyze_audio
from .config import VisualizerConfig
from .presets import get_theme
from .renderer import available_effect_names, render_visualizer_video


def run_visualizer(config: VisualizerConfig) -> Path:
    _validate_config(config)

    theme = get_theme(config.theme)
    features = analyze_audio(
        song_path=config.song_path,
        fps=config.fps,
        sample_rate=config.sample_rate,
        clip_seconds=config.clip_seconds,
    )
    return render_visualizer_video(config=config, theme=theme, features=features)


def _validate_config(config: VisualizerConfig) -> None:
    if config.fps <= 0:
        raise ValueError("fps must be greater than 0")
    if config.width <= 0 or config.height <= 0:
        raise ValueError("width and height must be greater than 0")
    if config.sample_rate <= 0:
        raise ValueError("sample_rate must be greater than 0")
    if config.clip_seconds < 0:
        raise ValueError("clip_seconds must be >= 0")
    if config.swap_every_bars <= 0:
        raise ValueError("swap_every_bars must be greater than 0")
    if config.beats_per_bar <= 0:
        raise ValueError("beats_per_bar must be greater than 0")
    if not config.effect_names:
        raise ValueError("effect_names cannot be empty")

    known_effects = set(available_effect_names())
    unknown_effects = sorted({name for name in config.effect_names if name not in known_effects})
    if unknown_effects:
        known_list = ", ".join(available_effect_names())
        unknown_list = ", ".join(unknown_effects)
        raise ValueError(f"Unknown effect_names: {unknown_list}. Choose from: {known_list}")
