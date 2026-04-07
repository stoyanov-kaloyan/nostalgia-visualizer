# Nostalgia Visualizer

Reusable Python **library + CLI** for music visualizers, tuned to a glitch-heavy black-background style with sporadic colorful bursts, bar-synced effect switching, and an optional live reactive window mode.

## Setup (uv + venv)

```bash
uv sync
source .venv/bin/activate
```

## CLI quick start (file render)

1. Put a song file at `assets/song.mp3` (or set another path in `visualizer.toml`).
1. Render:

```bash
uv run nostalgia-visualizer
```

Output defaults to `renders/output.mp4` in **16:9 (1280x720)**.
The renderer shows a live frame progress bar while encoding.
`main.py` is kept as a thin wrapper around the library CLI.

## Live window mode (react to current audio)

List available input devices:

```bash
uv run nostalgia-visualizer --list-input-devices
```

Launch live mode:

```bash
uv run nostalgia-visualizer --live --live-device 3 --theme blackout_glitch --effects glitch_bands,chroma_echo,tear_lines
```

- Press `Space` to force-switch to the next effect.
- Press `Esc` or `q` to close the window.
- For **PC/system audio** on Linux, choose a PulseAudio/PipeWire **monitor** input device.
- Live mode depends on PortAudio (`sudo apt install libportaudio2` on Ubuntu/Debian).

## Library usage

```python
from nostalgia_visualizer import render_song

render_song(
    song_path="assets/song.mp3",
    output_path="renders/my-reel.mp4",
    clip_seconds=20,
    theme="crt_breaker",
    effect_names=("glitch_bands", "chroma_echo", "scan_fall"),
    swap_every_bars=2,
)
```

You can also load from TOML and override on call:

```python
from nostalgia_visualizer import render_from_config

render_from_config("visualizer.toml", output_path="renders/custom.mp4", fps=24)
```

Launch the live window from Python:

```python
from nostalgia_visualizer import launch_live_visualizer

launch_live_visualizer(
    config_path="visualizer.toml",
    input_device=3,
    width=1280,
    height=720,
)
```

## Public API

- `render_song(...)`
- `render_from_config(...)`
- `render_with_config(...)`
- `launch_live_visualizer(...)`
- `load_config(...)` / `VisualizerConfig`
- `available_theme_names()`
- `available_effect_names()`
- `list_live_input_devices()`

## Visualizer system design

The renderer is intentionally hard-cut and glitchy:

1. **Audio feature layer (`audio.py`)**: extracts energy, onset, beat pulse, and spectral warmth from one song.
1. **Mood mapping layer (`presets.py`)**: applies a named glitch theme with a black base + neon palette.
1. **Effect engine (`renderer.py`)**: offers multiple glitch variants (`glitch_bands`, `chroma_echo`, `scan_fall`, `pixel_mosaic`, `tear_lines`).
1. **Bar scheduler (`renderer.py`)**: rotates through configured effects every N musical bars (beat-tracked, with tempo fallback).
1. **Frame synthesis layer (`renderer.py`)**:
   - black background foundation
   - effect-specific glitch layers
   - sporadic colorful blocks / sparks triggered by rhythm
   - scanlines, channel splits, grain, and strobe flashes
1. **Pipeline layer (`pipeline.py`)**: analyzes audio, renders frames, then muxes audio + video into a reel-ready MP4.
1. **Live layer (`live.py`)**: opens a realtime window, captures audio input, detects beats/onsets, and drives effect switching live.

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
effect_names = ["glitch_bands", "chroma_echo", "scan_fall", "pixel_mosaic", "tear_lines"]
swap_every_bars = 2
beats_per_bar = 4
seed = 7

[live]
input_device = ""
```

`clip_seconds = 0` renders the full song.

## CLI overrides

```bash
uv run nostalgia-visualizer --song assets/my-track.wav --theme crt_breaker --effects glitch_bands,chroma_echo,scan_fall --swap-every-bars 2 --clip-seconds 20
```

Live override example:

```bash
uv run nostalgia-visualizer --live --live-device 3 --effects glitch_bands,pixel_mosaic,tear_lines --swap-every-bars 1
```

List themes:

```bash
uv run nostalgia-visualizer --list-themes
```

List effects:

```bash
uv run nostalgia-visualizer --list-effects
```

List input devices:

```bash
uv run nostalgia-visualizer --list-input-devices
```

Run the standalone reusable example script:

```bash
uv run python examples/library_usage.py
```
