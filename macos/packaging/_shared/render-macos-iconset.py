#!/usr/bin/env python3
"""Build AppIcon.iconset PNGs with macOS-style squircle corners (Apple ~22.37% radius)."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

# iconutil iconset members: (pixel size, filename)
ICONSET_SIZES: list[tuple[int, str]] = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]

# Apple app-icon grid corner radius (fraction of side length)
CORNER_RATIO = 0.2237


def squircle_mask(size: int) -> Image.Image:
    """Rounded-rect mask matching macOS app-icon silhouette."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    radius = max(1, int(round(size * CORNER_RATIO)))
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def render_icon(src: Path, size: int) -> Image.Image:
    base = Image.open(src).convert("RGBA")
    base = base.resize((size, size), Image.Resampling.LANCZOS)
    mask = squircle_mask(size)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <source.png> <iconset_dir>", file=sys.stderr)
        return 1

    src = Path(sys.argv[1])
    iconset = Path(sys.argv[2])
    if not src.is_file():
        print(f"error: missing source: {src}", file=sys.stderr)
        return 1

    iconset.mkdir(parents=True, exist_ok=True)
    for size, name in ICONSET_SIZES:
        render_icon(src, size).save(iconset / name, format="PNG", optimize=True)

    print(f"OK: iconset -> {iconset} ({len(ICONSET_SIZES)} sizes, squircle mask)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
