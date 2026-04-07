from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    background_color: tuple[int, int, int]
    palette: tuple[tuple[int, int, int], ...]
    glitch_intensity: float
    scanline_strength: float
    grain_strength: float


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    cleaned = value.lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Invalid color value: {value}")
    return tuple(int(cleaned[i : i + 2], 16) for i in (0, 2, 4))


THEMES: dict[str, Theme] = {
    "blackout_glitch": Theme(
        name="blackout_glitch",
        background_color=_hex_to_rgb("#000000"),
        palette=(
            _hex_to_rgb("#FF006E"),
            _hex_to_rgb("#3A86FF"),
            _hex_to_rgb("#00F5D4"),
            _hex_to_rgb("#FB5607"),
            _hex_to_rgb("#FFBE0B"),
        ),
        glitch_intensity=1.0,
        scanline_strength=0.30,
        grain_strength=0.26,
    ),
    "crt_breaker": Theme(
        name="crt_breaker",
        background_color=_hex_to_rgb("#010101"),
        palette=(
            _hex_to_rgb("#F72585"),
            _hex_to_rgb("#4CC9F0"),
            _hex_to_rgb("#7209B7"),
            _hex_to_rgb("#B8F2E6"),
            _hex_to_rgb("#F5B700"),
        ),
        glitch_intensity=1.2,
        scanline_strength=0.35,
        grain_strength=0.31,
    ),
    "burnt_pixel": Theme(
        name="burnt_pixel",
        background_color=_hex_to_rgb("#020202"),
        palette=(
            _hex_to_rgb("#FF4D6D"),
            _hex_to_rgb("#FFD60A"),
            _hex_to_rgb("#2EC4B6"),
            _hex_to_rgb("#9381FF"),
            _hex_to_rgb("#00BBF9"),
        ),
        glitch_intensity=1.35,
        scanline_strength=0.27,
        grain_strength=0.38,
    ),
}


def get_theme(name: str) -> Theme:
    if name not in THEMES:
        names = ", ".join(available_theme_names())
        raise ValueError(f"Unknown theme '{name}'. Choose one of: {names}")
    return THEMES[name]


def available_theme_names() -> list[str]:
    return sorted(THEMES)
