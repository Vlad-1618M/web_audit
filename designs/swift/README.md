# Web Audit — macOS Swift app mockups

HTML wireframes for a **stupid-simple** native Mac app for site owners (Jill / flower shop / construction business).

**Implemented app:** [macos/WebAuditMac/](../../macos/WebAuditMac/) — runnable SwiftUI prototype (`swift build` / `./run-dev.sh`).  
**Full code & architecture guide (non-Swift devs):** [SWIFT_APP_GUIDE.md](../../macos/WebAuditMac/SWIFT_APP_GUIDE.md)

**Audience:** zero terminal skill · one URL · report opens in Safari · share with developer.

**Engine (under the hood, hidden from main UI):** `webaudit-docker` on PATH (recommended) or native `webaudit` CLI — see Advanced disclosure in the app.

---

## Preview

```bash
open designs/swift/index.html
# or a single screen:
open designs/swift/01-ready.html
```

Works offline. User flow diagram on the gallery page uses Mermaid CDN (network on first load).

---

## Screens (5)

| # | File | State |
|---|------|--------|
| 01 | [01-ready.html](01-ready.html) | Idle — URL field + **Scan my website** |
| 02 | [02-scanning.html](02-scanning.html) | In progress — **scrolling live log** (stdout / `-v` lines) |
| 03 | [03-complete.html](03-complete.html) | Success — **Open in browser** · **Download HTML** · Share |
| 04 | [04-error.html](04-error.html) | Invalid URL or scan failed — friendly fix hints |
| 05 | [05-help-advanced.html](05-help-advanced.html) | “What is this?” sheet + **Advanced** disclosure (no Docker in main copy) |

Shared chrome: [swift-mock.css](swift-mock.css) — macOS window, traffic lights, SF-style system fonts.

**Branding:** footer matches webapp / `web_audit.sh` attribution —
**Powered by [muzar.io](https://muzar.io/)** · **[GitHub](https://github.com/Vlad-1618M)** · © 2026 Vtools. All rights reserved.
(Copy source: [_footer-snippet.html](_footer-snippet.html))

**Scanning UX:** live log panel auto-scrolls as `webaudit` stdout arrives (Swift: `Process` pipe → `TextEditor` / `ScrollViewReader`).

---

## User flow

See [user-flow.md](user-flow.md) for full Mermaid diagrams (happy path, errors, post-scan actions).

---

## Swift implementation (done — see guide)

| UI element | Swift file / type |
|------------|-------------------|
| Window | `WebAuditMacApp.swift` — `WindowGroup` ~1280×1240 (wider than these mockups) |
| URL | `MacURLTextField.swift` — AppKit `NSTextField` bridge |
| Scan | `ScanViewModel.startScan()` → `ScanRunner.runScan()` |
| Live log | `ContentView.LiveLogView` — `ScrollViewReader` auto-scroll |
| Complete summary | `ReportCompleteView` + `ScanReportSnapshot` from `audit_run.json` |
| Open report | `ScanViewModel.openReportInBrowser()` → `NSWorkspace` |
| Download | `NSSavePanel` in `downloadReport()` |
| Share | `NSSharingServicePicker` in `shareReport()` |
| Help sheet | `ContentView.HelpSheet` |
| Advanced | Footer `DisclosureGroup` — engine path, reports dir |

Detail: [SWIFT_APP_GUIDE.md](../../macos/WebAuditMac/SWIFT_APP_GUIDE.md)

**Beyond mockups:** session history (up to 10 scans), in-app score dashboard, v1 shell edition escape hatch, `AboutDisclaimerPanel`.

**Out of scope:** menu bar extra, App Store sandbox, authenticated scans, bundled engine inside `.app`.

**Faster prototype:** same flow in [../platypus/](../platypus/) (Platypus.app shell wrapper — not PyGObject).

---

## Related

- Plain-English product copy: [v2_python_core/docs/getting_started_plain.md](../v2_python_core/docs/getting_started_plain.md)
- Report output (opens in browser): owner HTML variant in `v2_python_core/webaudit/templates/reports/`
- Platypus fast path (same UX, shell wrapper): brainstorm — `macos/platypus/` TBD
