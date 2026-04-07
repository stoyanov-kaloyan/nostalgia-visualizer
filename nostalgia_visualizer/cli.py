from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .api import render_from_config
from .presets import available_theme_names


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a black-background glitch music visualizer for a single preloaded song."
    )
    parser.add_argument("--config", type=Path, help="Path to a TOML config file.")
    parser.add_argument("--song", type=Path, help="Override the configured song path.")
    parser.add_argument("--output", type=Path, help="Override the configured output .mp4 path.")
    parser.add_argument("--theme", choices=available_theme_names(), help="Visual style preset.")
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
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_themes:
        print("\n".join(available_theme_names()))
        return

    output_path = render_from_config(
        config_path=args.config,
        song_path=args.song,
        output_path=args.output,
        theme=args.theme,
        clip_seconds=args.clip_seconds,
        fps=args.fps,
        width=args.width,
        height=args.height,
    )
    print(f"Rendered visualizer to {output_path}")
