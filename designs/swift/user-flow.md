# Web Audit Mac app — user flow

*Companion to HTML mockups in this folder. Renders on GitHub; also embedded in [index.html](index.html).*

---

## Happy path (site owner)

```mermaid
flowchart TD
  A([Launch Web Audit.app]) --> B[Main window: URL field empty]
  B --> C{User taps Scan my website}
  C --> D{Valid https URL?}
  D -->|No| E[Show error banner + highlight field]
  E --> B
  D -->|Yes| F[Disable button · show live log panel]
  F --> G[Run webaudit scan · pipe stdout/stderr]
  G --> H[Append each line · auto-scroll log]
  H --> I{Scan succeeded?}
  I -->|No| J[Error state: site down / blocked / network]
  J --> B
  I -->|Yes| K[Show Report ready + verdict summary]
  K --> L{User action}
  L --> M[Open report in browser]
  L --> N[Download report HTML]
  L --> O[Show in Finder]
  L --> P[Share → Mail / AirDrop / Messages]
  L --> Q[Scan another website → back to B]
  M --> R([Owner HTML report in Safari])
```

---

## Information architecture (one window)

```mermaid
stateDiagram-v2
  [*] --> Ready
  Ready --> Scanning: Scan my website
  Scanning --> Complete: success
  Scanning --> Error: invalid URL / failure
  Error --> Ready: Try again
  Complete --> Ready: Scan another
  Complete --> Browser: Open report
  Browser --> Complete: user closes browser tab

  Ready --> HelpSheet: What is this?
  HelpSheet --> Ready: dismiss
  Ready --> Advanced: expand Advanced
  Advanced --> Ready: collapse
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

Friendly step summaries (optional subtitle) still map from pipeline names — see earlier mockup iteration in git history.

---

## Post-scan actions

```mermaid
flowchart LR
  R --> O[Open report in browser]
  R --> D[Download report HTML]
  R --> F[Show in Finder]
  R --> S[Share sheet]
  R --> E[Email to developer optional v2]

  O --> B[Safari / default browser]
  D --> DL[Save As dialog or Desktop]
  F --> FD[~/Documents/WebAudit/…]
  S --> M[Mail · AirDrop · Messages]
```

---

## What we deliberately hide

```mermaid
flowchart TB
  subgraph main [Main UI — Jill]
    URL[Website URL]
    BTN[Scan button]
    STEPS[Friendly steps]
    OPEN[Open / Share]
  end

  subgraph advanced [Advanced disclosure only]
    VER[webaudit version]
    PATH[Output folder path]
    LOG[Copy log]
  end

  subgraph never [Not in owner v1]
    DOCK[Docker]
    GHCR[GHCR / image pull]
    TERM[Terminal]
  end

  URL --> BTN --> STEPS --> OPEN
  advanced -.->|optional| main
  never -.x main
```

---

## Engine options (implementation, not UI)

| Phase | Engine | Jill sees |
|-------|--------|-----------|
| Prototype | Platypus + `webaudit-docker.sh` | Same mockups |
| v1 app | Bundled `webaudit` in app Resources | Same mockups |
| Dev-only | Docker via Advanced | Hidden by default |

---

## Window spec (Swift target)

| Property | Value |
|----------|--------|
| Default size | 480 × 420 pt (resizable min 440 × 380) |
| Style | Standard titled window, traffic lights |
| Primary action | Scan my website (default button) |
| Reports path | `~/Documents/WebAudit/` default |
| Branding | Footer: Powered by [muzar.io](https://muzar.io/) · [GitHub](https://github.com/Vlad-1618M) · © Vtools. All rights reserved. |
| External links | Help → GitHub plain-English doc or your site |
