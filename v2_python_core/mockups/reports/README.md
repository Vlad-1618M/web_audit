# Report UI mockups

Five dark-theme HTML report variants for Web Audit v2. **CSS lives in sibling files** — same layout I will use with Jinja2 templates later.

**Start here:** [index.html](index.html) — gallery with live previews of all five variants.

## Theme

- **Black background** (`#030306`) with subtle radial glows
- **Rich accent colors** — cyan, magenta, gold, lime, violet, coral
- **Edge-lit buttons** on sensitive actions (PDF, JSON, share, re-run) via `shared-dark.css`
- No white backgrounds — print/PDF uses `print-color-adjust: exact`

## Variants

| ID | Audience | Files |
|----|----------|-------|
| **A · Executive** | Site owner, non-technical | [variant-a-executive.html](variant-a-executive.html) + [executive.css](executive.css) |
| **B · Technical** | Developers, dev shops | [variant-b-technical.html](variant-b-technical.html) + [technical.css](technical.css) |
| **C · Minimal** | One-page handoff / print / PDF | [variant-c-minimal.html](variant-c-minimal.html) + [minimal.css](minimal.css) |
| **D · Dashboard** | CI monitors, at-a-glance metrics | [variant-d-dashboard.html](variant-d-dashboard.html) + [dashboard.css](dashboard.css) |
| **E · Owner digest** | Timeline narrative for payers | [variant-e-digest.html](variant-e-digest.html) + [digest.css](digest.css) |

Shared foundation: [shared-dark.css](shared-dark.css) (imported by each variant CSS).

## Preview

```bash
open v2_python_core/mockups/reports/index.html   # all variants
open v2_python_core/mockups/reports/variant-a-executive.html
```

## Button classes (edge lighting)

| Class | Use |
|-------|-----|
| `btn-edge-cyan` | Export PDF, primary download |
| `btn-edge-magenta` | JSON, share, email to dev |
| `btn-edge-gold` | Secondary export (SARIF, handoff) |
| `btn-edge-danger` | Re-run scan, destructive actions |

## PDF (v2 vs v1)

**v1 bash:** “Save as PDF” → browser print dialog.

**v2 Python:** WeasyPrint renders same HTML+CSS server-side. Dark theme preserved with `print-color-adjust: exact`.

## Template mapping (future)

```text
templates/reports/executive/   ← variant A
templates/reports/technical/   ← variant B
templates/reports/minimal/     ← variant C
templates/reports/dashboard/   ← variant D
templates/reports/digest/      ← variant E
```

Python `render/` only loads templates and passes `AuditRun` context — no inline styles in `.py` files.

## Sample data

All mockups use fictional **Acme Widgets Co.** (`https://acme-widgets.com`).
