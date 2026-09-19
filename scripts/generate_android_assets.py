#!/usr/bin/env python3
"""Write PWA and Android launcher PNGs with the stdlib (no Pillow)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STONE = (28, 25, 23, 255)
AMBER = (180, 83, 9, 255)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, pixels: list[list[tuple[int, int, int, int]]]) -> None:
    height = len(pixels)
    width = len(pixels[0])
    raw = b"".join(
        b"\x00" + b"".join(struct.pack("BBBB", *px) for px in row) for row in pixels
    )
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    payload += _chunk(b"IDAT", zlib.compress(raw, 9))
    payload += _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _in_circle(x: int, y: int, cx: float, cy: float, r: float) -> bool:
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def _in_six(x: int, y: int, size: int) -> bool:
    """Rough '6' glyph in the inner 60% of a square icon."""
    s = size
    cx, cy = s * 0.50, s * 0.54
    outer, inner = s * 0.22, s * 0.12
    if not _in_circle(x, y, cx, cy, outer):
        left, right = s * 0.30, s * 0.42
        top, bot = s * 0.22, cy
        return left <= x <= right and top <= y <= bot
    return not _in_circle(x, y, cx, cy, inner)


def render_icon(size: int, *, round_mask: bool = False) -> list[list[tuple[int, int, int, int]]]:
    rows: list[list[tuple[int, int, int, int]]] = []
    cx = cy = (size - 1) / 2
    radius = size * 0.48
    for y in range(size):
        row = []
        for x in range(size):
            if round_mask and not _in_circle(x, y, cx, cy, radius):
                row.append((0, 0, 0, 0))
                continue
            if _in_six(x, y, size):
                row.append(AMBER)
            else:
                row.append(STONE)
        rows.append(row)
    return rows


def render_foreground(size: int) -> list[list[tuple[int, int, int, int]]]:
    """Adaptive-icon foreground with transparent padding."""
    rows: list[list[tuple[int, int, int, int]]] = []
    for y in range(size):
        row = []
        for x in range(size):
            inset = size * 0.18
            if x < inset or y < inset or x >= size - inset or y >= size - inset:
                row.append((0, 0, 0, 0))
            elif _in_six(x, y, size):
                row.append(AMBER)
            else:
                row.append((0, 0, 0, 0))
        rows.append(row)
    return rows


def main() -> None:
    icons = ROOT / "web/public/icons"
    write_png(icons / "icon-192.png", render_icon(192))
    write_png(icons / "icon-512.png", render_icon(512))

    res = ROOT / "web/android/app/src/main/res"
    densities = {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }
    fg_scale = 2.25
    for name, size in densities.items():
        folder = res / f"mipmap-{name}"
        write_png(folder / "ic_launcher.png", render_icon(size))
        write_png(folder / "ic_launcher_round.png", render_icon(size, round_mask=True))
        write_png(folder / "ic_launcher_foreground.png", render_foreground(int(size * fg_scale)))

    print(f"Wrote PWA icons under {icons}")
    print(f"Wrote Android mipmaps under {res}")


if __name__ == "__main__":
    main()
