from __future__ import annotations

import argparse
from pathlib import Path

from nostalgia_visualizer.config import load_config
from nostalgia_visualizer.pipeline import run_visualizer
from nostalgia_visualizer.presets import available_theme_names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render a black-background glitch music visualizer for a single preloaded song."
        )
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.list_themes:
        print("\n".join(available_theme_names()))
        return

    config = load_config(args.config)
    if args.song is not None:
        config.song_path = args.song
    if args.output is not None:
        config.output_path = args.output
    if args.theme is not None:
        config.theme = args.theme
    if args.clip_seconds is not None:
        config.clip_seconds = args.clip_seconds
    if args.fps is not None:
        config.fps = args.fps
    if args.width is not None:
        config.width = args.width
    if args.height is not None:
        config.height = args.height

    output_path = run_visualizer(config)
    print(f"Rendered visualizer to {output_path}")


if __name__ == "__main__":
    main()
