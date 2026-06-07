#!/usr/bin/env python3
"""Generate retina DMG background (2× window size @ 144 DPI). Keep in sync with dmg-layout.env."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ReportTheme-ish palette
CANVAS = (3, 3, 6)
SURFACE = (14, 14, 22)
LIME = (57, 255, 140)
TEXT = (238, 242, 255)
MUTED = (139, 149, 176)

SCALE = 2
# Finder maps pixel size → points as: points = pixels * 72 / dpi.
# A 2× background must be 144 DPI so 1320px → 660pt (not 1320pt).
BACKGROUND_DPI = 144
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
        "WIN_H": 440,
        "ICON_SIZE": 128,
        "APP_X": 168,
        "APP_Y": 170,
        "APPS_X": 492,
        "APPS_Y": 170,
        "INSTALL_X": 88,
        "INSTALL_Y": 290,
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


def _stamp_dpi(path: Path, dpi: int) -> None:
    subprocess.run(
        ["sips", "-s", "dpiWidth", str(dpi), "-s", "dpiHeight", str(dpi), str(path)],
        check=True,
        capture_output=True,
    )


def main() -> None:
    layout = _load_layout()
    win_w = layout["WIN_W"]
    win_h = layout["WIN_H"]
    icon_size = layout["ICON_SIZE"]
    w = win_w * SCALE
    h = win_h * SCALE

    app_x = layout["APP_X"] * SCALE
    apps_x = layout["APPS_X"] * SCALE
    # create-dmg icon Y is the top edge of the icon row (1× points, origin top-left).
    icon_row_top = layout["APP_Y"] * SCALE
    icon_center_y = icon_row_top + (icon_size * SCALE // 2)
    half_icon = icon_size * SCALE // 2

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

    ax1 = app_x + half_icon + 12 * SCALE
    ax2 = apps_x - half_icon - 12 * SCALE
    draw.line([(ax1, icon_center_y), (ax2, icon_center_y)], fill=MUTED, width=3 * SCALE)
    draw.polygon(
        [
            (ax2 - 20 * SCALE, icon_center_y - 12 * SCALE),
            (ax2, icon_center_y),
            (ax2 - 20 * SCALE, icon_center_y + 12 * SCALE),
        ],
        fill=LIME,
    )

    # Center band only — INSTALL.txt sits bottom-left (see dmg-layout.env).
    icon_row_bottom = icon_row_top + icon_size * SCALE + 22 * SCALE
    hint_y = icon_row_bottom + 18 * SCALE
    draw.text(
        (w // 2, hint_y),
        "Drag Web Audit to Applications",
        font=hint_font,
        fill=TEXT,
        anchor="mm",
    )
    draw.text(
        (w // 2, hint_y + 26 * SCALE),
        "First launch: Right-click → Open if macOS asks",
        font=hint_font,
        fill=MUTED,
        anchor="mm",
    )
    draw.text(
        (w // 2, win_h * SCALE - 34 * SCALE),
        "Powered by muzar.io  ·  © Vtools",
        font=foot_font,
        fill=MUTED,
        anchor="mm",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", dpi=(BACKGROUND_DPI, BACKGROUND_DPI), optimize=True)
    _stamp_dpi(OUT, BACKGROUND_DPI)
    print(f"OK: {OUT} ({w}x{h} @ {BACKGROUND_DPI} DPI → {win_w}x{win_h} pt window)")


if __name__ == "__main__":
    main()
