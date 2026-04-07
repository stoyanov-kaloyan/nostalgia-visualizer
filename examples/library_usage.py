from pathlib import Path

from nostalgia_visualizer import render_song


def main() -> None:
    output = render_song(
        song_path=Path("assets/song.mp3"),
        output_path=Path("renders/library-example.mp4"),
        clip_seconds=12,
        theme="crt_breaker",
    )
    print(f"Library render complete: {output}")


if __name__ == "__main__":
    main()
