# Architecture diagrams (mockup)

Dark-themed Mermaid diagrams matching [report mockups](../reports/shared-dark.css).

## Preview

```bash
open v2_python_core/mockups/diagrams/index.html
```

Requires network on first load (Mermaid 11 from jsDelivr CDN).

## Contents

1. **Product focus** — pie: Hygiene 70% · Exposure 25% · SEO 5%
2. **Scoring vs informational** — Verdict driven by Hygiene + Exposure only
3. **Tier stack** — Tier 1 → 2 → 2b → 2c → 3
4. **Scan pipeline** — config, framework profile, core, output
5. **Finding classes** — ACTION vs VERIFY vs INFO
6. **Framework profile resolution** — sequence diagram

## Source

Markdown + embeddable blocks: [docs/diagrams.md](../../docs/diagrams.md)

GitHub renders Mermaid in `.md` with theme init blocks; browser mockup uses matching `themeVariables`.

## Palette

| Color | Hex | Meaning |
|-------|-----|---------|
| Cyan | `#00f0ff` | Primary / Tier 1 |
| Gold | `#ffc14d` | Hygiene |
| Lime | `#39ff8c` | Exposure / output |
| Violet | `#a855f7` | SEO surface |
| Magenta | `#ff0080` | Tier 2 / profiles |
| Background | `#030306` | Canvas |
