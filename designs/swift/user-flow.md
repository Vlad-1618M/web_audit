# Web Audit Mac app — user flow

*Companion to HTML mockups in this folder. Renders on GitHub; also embedded in [index.html](index.html).*

**Install paths:** [DELIVERY_PATHS.md](../../DELIVERY_PATHS.md) — public DMG (bundled engine) vs dev (Docker/venv).

---

## Happy path (site owner — public DMG)

```mermaid
flowchart TD
  A([Launch Web Audit.app]) --> B[Main window: URL field empty]
  B --> C{User taps Scan my website}
  C --> D{Valid https URL?}
  D -->|No| E[Error state: invalid URL]
  E --> T[Try again / Back to home]
  T --> B
  D -->|Yes| F[Disable button · show live log panel]
  F --> G[Run bundled webaudit · pipe stdout/stderr]
  G --> H[Append each line · auto-scroll log]
  H --> I{Scan succeeded?}
  I -->|No| J[Error state: failure log written]
  J --> T
  I -->|Yes| K[Show Report ready + verdict summary]
  K --> L{User action}
  L --> M[Open report in browser]
  L --> N[Save report to share zip]
  L --> O[Show in Finder]
  L --> P[Share → Mail / AirDrop / Messages]
  L --> Q[Scan another website → back to B]
  L --> R[Switch saved report / Back to home]
  M --> S([Owner HTML report in Safari])
```

---

## Information architecture (one window)

```mermaid
stateDiagram-v2
  [*] --> Ready
  Ready --> Scanning: Scan my website
  Scanning --> Complete: success
  Scanning --> Error: invalid URL / failure
  Error --> Ready: Try again / Back to home
  Complete --> Ready: Scan another / Back to home
  Complete --> Browser: Open report
  Browser --> Complete: user closes browser tab

  Ready --> HelpSheet: Learn more
  HelpSheet --> Ready: dismiss
  Ready --> Advanced: expand Advanced
  Advanced --> Ready: collapse
  Complete --> SavedList: pick another report
  SavedList --> Complete: switch report
```

---

## Step label mapping (scan progress)

Primary UX is the **scrolling live log** (same lines as `webaudit scan -v`). Optional headline can track the current `▸` step:

```mermaid
flowchart LR
  subgraph stdout [Stdout line]
    L1["▸ headers …"]
    L2["✔ paths …"]
    L3["→ /admin OPEN …"]
  end

  subgraph ui [Log panel]
    U[Append + scroll to bottom]
  end

  L1 --> U
  L2 --> U
  L3 --> U
```

---

## Post-scan actions

```mermaid
flowchart LR
  R[Report ready] --> O[Open report in browser]
  R --> D[Save report to share zip]
  R --> F[Show in Finder]
  R --> S[Share sheet]
  R --> Z[Zip all saved reports]
  R --> H[Home / switch saved report]

  O --> B[Safari / default browser]
  D --> DL[Save As dialog]
  F --> FD["~/Documents/WebAudit/…"]
  S --> M[Mail · AirDrop · Messages]
```

---

## What we deliberately hide (public DMG)

```mermaid
flowchart TB
  subgraph main [Main UI — site owner]
    URL[Website URL]
    BTN[Scan button]
    LOG[Live log]
    OPEN[Open / Share / Saved reports]
  end

  subgraph advanced [Advanced disclosure only]
    VER[webaudit version]
    PATH[Output folder path]
    ENG[Engine policy: bundled]
  end

  subgraph never [Not in public install copy]
    DOCK[Docker setup]
    GHCR[GHCR / image pull]
    TERM[Terminal commands]
  end

  URL --> BTN --> LOG --> OPEN
  advanced -.->|optional| main
  never -.x main
```

---

## Engine options (implementation, not main UI)

| Path | Engine | User sees |
|------|--------|-----------|
| **A — Public DMG** | Bundled `Resources/Engine/bin/webaudit` | Same mockups — no Docker |
| **C — Dev app** | `webaudit-docker` or `.venv` / PATH | Advanced shows external engine |
| **Deferred** | Platypus + shell wrapper | Mockups only — [../platypus/](../platypus/) |

See [DELIVERY_PATHS.md](../../DELIVERY_PATHS.md).

---

## Window spec (Swift target)

| Property | Value |
|----------|--------|
| Default size | ~1280 × 1240 pt (resizable; mockups are smaller) |
| Style | Standard titled window, traffic lights |
| Primary action | Scan my website (default button) |
| Reports path | `~/Documents/WebAudit/` |
| Failure logs | `~/Documents/WebAudit/Logs/` |
| Branding | Footer: Powered by [muzar.io](https://muzar.io/) · [GitHub](https://github.com/Vlad-1618M) · © Vtools |
| Help | **Learn more** → plain-English doc, install guide, shell V1, contact |
