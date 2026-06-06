#!/usr/bin/env python3
"""Generate retina DMG background (1320x800 for 660x400 window). Keep in sync with dmg-layout.env."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ReportTheme-ish palette
CANVAS = (3, 3, 6)
SURFACE = (14, 14, 22)
LIME = (57, 255, 140)
TEXT = (238, 242, 255)
MUTED = (139, 149, 176)

SCALE = 2
OUT = Path(__file__).resolve().parent / "dmg-background.png"
LAYOUT_ENV = Path(__file__).resolve().parent / "dmg-layout.env"


def _load_layout() -> dict[str, int]:
    values: dict[str, int] = {}
    if LAYOUT_ENV.exists():
        for line in LAYOUT_ENV.read_text().splitlines():
            m = re.match(r"export DMG_(\w+)=(\d+)", line.strip())
            if m:
                values[m.group(1)] = int(m.group(2))
    defaults = {
        "WIN_W": 660,
        "WIN_H": 400,
        "APP_X": 168,
        "APP_Y": 212,
        "APPS_X": 492,
        "APPS_Y": 212,
    }
    for key, val in defaults.items():
        values.setdefault(key, val)
    return values


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def main() -> None:
    layout = _load_layout()
    w = layout["WIN_W"] * SCALE
    h = layout["WIN_H"] * SCALE

    app_x = layout["APP_X"] * SCALE
    apps_x = layout["APPS_X"] * SCALE
    row_y = layout["APP_Y"] * SCALE
    half_icon = 64 * SCALE  # 128px icon @1x

    img = Image.new("RGB", (w, h), CANVAS)
    draw = ImageDraw.Draw(img)

    for y in range(100 * SCALE):
        t = y / (100 * SCALE)
        color = tuple(int(CANVAS[i] * (1 - t) + SURFACE[i] * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=color)

    title_font = _font(48 * SCALE // 2, bold=True)
    hint_font = _font(22 * SCALE // 2)
    foot_font = _font(18 * SCALE // 2)

    title_y = 58 * SCALE
    line_y = 98 * SCALE
    draw.text((w // 2, title_y), "Web Audit for Mac", font=title_font, fill=TEXT, anchor="mm")
    draw.rectangle([(60 * SCALE, line_y), (w - 60 * SCALE, line_y + 4)], fill=LIME)

    # Arrow between icon centers (no subtitle over the icon row — avoids overlap)
    ax1 = app_x + half_icon + 12 * SCALE
    ax2 = apps_x - half_icon - 12 * SCALE
    ay = row_y
    draw.line([(ax1, ay), (ax2, ay)], fill=MUTED, width=3 * SCALE)
    draw.polygon(
        [
            (ax2 - 20 * SCALE, ay - 12 * SCALE),
            (ax2, ay),
            (ax2 - 20 * SCALE, ay + 12 * SCALE),
        ],
        fill=LIME,
    )

    draw.text(
        (w // 2, 268 * SCALE),
        "First launch: Right-click → Open  (unsigned build)",
        font=hint_font,
        fill=MUTED,
        anchor="mm",
    )
    draw.text(
        (w // 2, 355 * SCALE),
        "Powered by muzar.io  ·  © Vtools",
        font=foot_font,
        fill=MUTED,
        anchor="mm",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print(f"OK: {OUT} ({w}x{h})")


if __name__ == "__main__":
    main()
