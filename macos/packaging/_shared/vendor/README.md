# create-dmg (vendored)

Upstream: [create-dmg/create-dmg](https://github.com/create-dmg/create-dmg) v1.2.3

Used by `make-styled-dmg.sh` for DMG window layout (background, icon positions, Applications drop link).

To refresh:

```bash
curl -fsSL -o vendor/create-dmg https://raw.githubusercontent.com/create-dmg/create-dmg/master/create-dmg
chmod +x vendor/create-dmg
# support/template.applescript + support/eula-resources-template.xml from same repo
```

Background art: `../dmg-background.png` (regenerate with `../generate-dmg-background.py` — needs Pillow).

**DPI:** The 2× PNG must be **144 DPI** so Finder maps 1320×800 px → 660×400 pt. At 72 DPI the background renders at double size and the window looks cropped until the user resizes manually.
