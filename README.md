# Nostalgia Visualizer

Offline Python visualizer for **one preloaded song at a time**, now tuned to a **glitch-heavy black-background** look with sporadic colorful bursts.

## Setup (uv + venv)

```bash
uv sync
source .venv/bin/activate
```

## Quick start

1. Put a song file at `assets/song.mp3` (or set another path in `visualizer.toml`).
1. Render:

```bash
uv run python main.py
```

Output defaults to `renders/nostalgia-reel.mp4` in **16:9 (1280x720)**.
The renderer shows a live frame progress bar while encoding.

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
output_path = "renders/nostalgia-reel.mp4"
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
uv run python main.py --song assets/my-track.wav --theme crt_breaker --clip-seconds 20
```

List themes:

```bash
uv run python main.py --list-themes
```
