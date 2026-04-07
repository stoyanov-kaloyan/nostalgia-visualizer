from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

DEFAULT_CONFIG_PATH = Path("visualizer.toml")


@dataclass(slots=True)
class VisualizerConfig:
    song_path: Path = Path("assets/song.mp3")
    output_path: Path = Path("renders/output.mp4")
    width: int = 1280
    height: int = 720
    fps: int = 30
    sample_rate: int = 44_100
    clip_seconds: float = 30.0
    theme: str = "blackout_glitch"
    seed: int = 7


def load_config(path: Path | None = None) -> VisualizerConfig:
    config = VisualizerConfig()
    config_path = path or DEFAULT_CONFIG_PATH
    if path is not None and not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    if not config_path.exists():
        return config

    with config_path.open("rb") as config_file:
        raw_config = tomllib.load(config_file)

    _apply_audio_section(config, raw_config.get("audio", {}))
    _apply_video_section(config, raw_config.get("video", {}))
    _apply_style_section(config, raw_config.get("style", {}))

    base_dir = config_path.parent
    if not config.song_path.is_absolute():
        config.song_path = (base_dir / config.song_path).resolve()
    if not config.output_path.is_absolute():
        config.output_path = (base_dir / config.output_path).resolve()

    return config


def _apply_audio_section(config: VisualizerConfig, section: dict[str, Any]) -> None:
    if not section:
        return
    if "song_path" in section:
        config.song_path = Path(str(section["song_path"]))
    if "sample_rate" in section:
        config.sample_rate = int(section["sample_rate"])
    if "clip_seconds" in section:
        config.clip_seconds = float(section["clip_seconds"])


def _apply_video_section(config: VisualizerConfig, section: dict[str, Any]) -> None:
    if not section:
        return
    if "output_path" in section:
        config.output_path = Path(str(section["output_path"]))
    if "width" in section:
        config.width = int(section["width"])
    if "height" in section:
        config.height = int(section["height"])
    if "fps" in section:
        config.fps = int(section["fps"])


def _apply_style_section(config: VisualizerConfig, section: dict[str, Any]) -> None:
    if not section:
        return
    if "theme" in section:
        config.theme = str(section["theme"])
    if "seed" in section:
        config.seed = int(section["seed"])
