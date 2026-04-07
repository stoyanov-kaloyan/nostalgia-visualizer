from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .api import render_from_config
from .presets import available_theme_names
from .renderer import available_effect_names


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a black-background glitch music visualizer for a single preloaded song."
    )
    parser.add_argument("--config", type=Path, help="Path to a TOML config file.")
    parser.add_argument("--song", type=Path, help="Override the configured song path.")
    parser.add_argument("--output", type=Path, help="Override the configured output .mp4 path.")
    parser.add_argument("--theme", choices=available_theme_names(), help="Visual style preset.")
    parser.add_argument(
        "--effects",
        help="Comma-separated effect names to rotate, e.g. glitch_bands,chroma_echo,scan_fall.",
    )
    parser.add_argument(
        "--swap-every-bars",
        type=int,
        help="How many musical bars to keep each effect before switching.",
    )
    parser.add_argument(
        "--beats-per-bar",
        type=int,
        help="Bar size used for effect switching.",
    )
    parser.add_argument(
        "--clip-seconds",
        type=float,
        help="Render duration. Use 0 to render the full song.",
    )
    parser.add_argument("--fps", type=int, help="Override frames per second.")
    parser.add_argument("--width", type=int, help="Override output width in pixels.")
    parser.add_argument("--height", type=int, help="Override output height in pixels.")
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="Print available themes and exit.",
    )
    parser.add_argument(
        "--list-effects",
        action="store_true",
        help="Print available effects and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_themes:
        print("\n".join(available_theme_names()))
        return
    if args.list_effects:
        print("\n".join(available_effect_names()))
        return

    try:
        effects = _parse_effects(args.effects)
    except ValueError as error:
        parser.error(str(error))

    output_path = render_from_config(
        config_path=args.config,
        song_path=args.song,
        output_path=args.output,
        theme=args.theme,
        effect_names=effects,
        swap_every_bars=args.swap_every_bars,
        beats_per_bar=args.beats_per_bar,
        clip_seconds=args.clip_seconds,
        fps=args.fps,
        width=args.width,
        height=args.height,
    )
    print(f"Rendered visualizer to {output_path}")


def _parse_effects(raw_effects: str | None) -> tuple[str, ...] | None:
    if raw_effects is None:
        return None
    effects = tuple(entry.strip() for entry in raw_effects.split(",") if entry.strip())
    if not effects:
        raise ValueError("Expected at least one effect name in --effects.")
    return effects
