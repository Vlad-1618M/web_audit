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

# qlmanage renders SVG transparency as opaque white — knock out before masking
_WHITE_FRINGE_THRESHOLD = 250


def squircle_mask(size: int) -> Image.Image:
    """Rounded-rect mask matching macOS app-icon silhouette."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    radius = max(1, int(round(size * CORNER_RATIO)))
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def _is_white_fringe_pixel(r: int, g: int, b: int, a: int) -> bool:
    return a > 0 and r >= _WHITE_FRINGE_THRESHOLD and g >= _WHITE_FRINGE_THRESHOLD and b >= _WHITE_FRINGE_THRESHOLD


def knock_out_white_fringe(image: Image.Image) -> Image.Image:
    """Remove qlmanage's white matte only when connected to the image edge.

    Interior white/cream label text must stay solid — a global white threshold
    would hollow out AUDIT and similar fills.
    """
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    to_clear: set[tuple[int, int]] = set()
    stack: list[tuple[int, int]] = []

    for x in range(width):
        for y in (0, height - 1):
            if _is_white_fringe_pixel(*pixels[x, y]):
                stack.append((x, y))
    for y in range(1, height - 1):
        for x in (0, width - 1):
            if _is_white_fringe_pixel(*pixels[x, y]):
                stack.append((x, y))

    while stack:
        x, y = stack.pop()
        if (x, y) in to_clear:
            continue
        if not _is_white_fringe_pixel(*pixels[x, y]):
            continue
        to_clear.add((x, y))
        if x > 0:
            stack.append((x - 1, y))
        if x < width - 1:
            stack.append((x + 1, y))
        if y > 0:
            stack.append((x, y - 1))
        if y < height - 1:
            stack.append((x, y + 1))

    for x, y in to_clear:
        r, g, b, _a = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
    return rgba


def render_icon(src: Path, size: int) -> Image.Image:
    base = Image.open(src).convert("RGBA")
    base = knock_out_white_fringe(base)
    base = base.resize((size, size), Image.Resampling.LANCZOS)
    mask = squircle_mask(size)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)
    return out


def main() -> int:
    if len(sys.argv) not in {3, 4}:
        print(
            f"Usage: {sys.argv[0]} <source.png> <iconset_dir> [master_1024.png]",
            file=sys.stderr,
        )
        return 1

    src = Path(sys.argv[1])
    iconset = Path(sys.argv[2])
    master_out = Path(sys.argv[3]) if len(sys.argv) == 4 else None
    if not src.is_file():
        print(f"error: missing source: {src}", file=sys.stderr)
        return 1

    iconset.mkdir(parents=True, exist_ok=True)
    for size, name in ICONSET_SIZES:
        render_icon(src, size).save(iconset / name, format="PNG", optimize=True)

    if master_out is not None:
        master_out.parent.mkdir(parents=True, exist_ok=True)
        render_icon(src, 1024).save(master_out, format="PNG", optimize=True)

    print(f"OK: iconset -> {iconset} ({len(ICONSET_SIZES)} sizes, squircle mask)")
    if master_out is not None:
        print(f"OK: master -> {master_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
