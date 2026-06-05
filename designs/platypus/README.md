# Web Audit — Platypus.app mockups

**Status: deferred** — mockups and example script only. **Shipped path:** native SwiftUI app + public DMG with bundled engine ([DELIVERY_PATHS.md](../../DELIVERY_PATHS.md) row **A**).

HTML previews of a **Platypus-wrapped** Mac app for site owners. Same user journey as [../swift/](../swift/) — different chrome (native dialogs + Progress Window).

> **Not PyGObject.** [Platypus](https://sveinbjorn.org/platypus) is a **macOS-only** utility that turns shell scripts into double-click `.app` bundles. **PyGObject** is Linux GTK/Python — different tool entirely. Easy to misread when tired.

---

## Preview

```bash
open designs/platypus/index.html
```

---

## Screens (5) — same flow as Swift

| # | File | Platypus equivalent |
|---|------|---------------------|
| 01 | [01-url-prompt.html](01-url-prompt.html) | Launch dialog / “Accept dropped text” URL input |
| 02 | [02-progress.html](02-progress.html) | **Progress Window** — stdout streams into text view |
| 03 | [03-complete.html](03-complete.html) | `osascript` alert — Open in browser / Download / Finder |
| 04 | [04-error.html](04-error.html) | Validation or scan failure alert |
| 05 | [05-help.html](05-help.html) | Help menu → dialog or open GitHub doc |

**Flow:** automatic like Swift — user enters URL → progress window → completion dialog. No manual “next screen” wizard.

---

## Platypus vs Swift (quick compare)

| | Platypus | Swift |
|---|----------|-------|
| **Build time** | Hours (you know it) | Days–weeks learning SwiftUI |
| **UI** | System dialogs + progress text view | Custom window, polished layout |
| **Live log** | Native — script `echo` → Progress Window | Pipe `Process` stdout → `TextEditor` |
| **Size** | Tiny `.app` + script | Small app + bundled `webaudit` later |
| **Engine** | Would call `webaudit-docker` on PATH | **Shipped:** bundled in public DMG |
| **Platform** | macOS only | macOS only |

---

## Example script

[example-scan.sh](example-scan.sh) — drop into Platypus.app:

- Prompt for URL (or `$1` from droplet)
- Run `webaudit-docker … --open none`
- Alert: Open in browser / Show in Finder
- Footer echo matches webapp attribution

**Platypus settings (suggested):**

- Interface: **Progress Bar** + remain open after execution
- Output: **Text window** (stream stdout/stderr)
- Bundled files: optional — or rely on installed `webaudit-docker`
- Icon: your Web Audit icon

---

## Window sizes (typical Platypus)

| Element | Approx. size |
|---------|----------------|
| Progress Window | **520 × 380 px** (configurable in Platypus) |
| Log text view | ~**280 px** tall (matches mockup 02) |
| URL / completion dialogs | **420 px** wide (system sheet style) |

Smaller than a full app window; feels like a **utility** — fine for Jill if icon + wording are clear.

---

## Branding

Same footer as Swift mockups: **Powered by [muzar.io](https://muzar.io/)** · **[GitHub](https://github.com/Vlad-1618M)** · © 2026 Vtools. All rights reserved.

---

## User flow

[user-flow.md](user-flow.md) · compare [../swift/user-flow.md](../swift/user-flow.md)

---

## Related

- Host wrapper the script calls: [v2_python_core/scripts/webaudit-docker.sh](../../v2_python_core/scripts/webaudit-docker.sh)
- Swift polish path: [../swift/](../swift/)
