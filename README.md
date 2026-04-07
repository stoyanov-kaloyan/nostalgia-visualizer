# Nostalgia Visualizer

Reusable Python **library + CLI** for one-preloaded-song visualizers, tuned to a glitch-heavy black-background style with sporadic colorful bursts.

## Setup (uv + venv)

```bash
uv sync
source .venv/bin/activate
```

## CLI quick start

1. Put a song file at `assets/song.mp3` (or set another path in `visualizer.toml`).
1. Render:

```bash
uv run nostalgia-visualizer
```

Output defaults to `renders/output.mp4` in **16:9 (1280x720)**.
The renderer shows a live frame progress bar while encoding.
`main.py` is kept as a thin wrapper around the library CLI.

## Library usage

```python
from nostalgia_visualizer import render_song

render_song(
    song_path="assets/song.mp3",
    output_path="renders/my-reel.mp4",
    clip_seconds=20,
    theme="crt_breaker",
)
```

You can also load from TOML and override on call:

```python
from nostalgia_visualizer import render_from_config

render_from_config("visualizer.toml", output_path="renders/custom.mp4", fps=24)
```

## Public API

- `render_song(...)`
- `render_from_config(...)`
- `render_with_config(...)`
- `load_config(...)` / `VisualizerConfig`
- `available_theme_names()`

## Visualizer system design

The renderer is intentionally hard-cut and glitchy:

1. **Audio feature layer (`audio.py`)**: extracts energy, onset, beat pulse, and spectral warmth from one song.
1. **Mood mapping layer (`presets.py`)**: applies a named glitch theme with a black base + neon palette.
1. **Frame synthesis layer (`renderer.py`)**:
   - black background foundation
   - horizontal glitch bands and offset channel splits
   - sporadic colorful blocks / sparks triggered by rhythm
   - scanlines, grain, and strobe flashes
1. **Pipeline layer (`pipeline.py`)**: analyzes audio, renders frames, then muxes audio + video into a reel-ready MP4.

## Configuration

Edit `visualizer.toml`:

```toml
[audio]
song_path = "assets/song.mp3"
sample_rate = 44100
clip_seconds = 30

[video]
output_path = "renders/output.mp4"
width = 1280
height = 720
fps = 30

[style]
theme = "blackout_glitch"
seed = 7
```

`clip_seconds = 0` renders the full song.

## CLI overrides

```bash
uv run nostalgia-visualizer --song assets/my-track.wav --theme crt_breaker --clip-seconds 20
```

List themes:

```bash
uv run nostalgia-visualizer --list-themes
```

Run the standalone reusable example script:

```bash
uv run python examples/library_usage.py
```
