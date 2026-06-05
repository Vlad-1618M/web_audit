# Web Audit Platypus app — user flow

Same journey as [Swift mockups](../swift/user-flow.md); Platypus uses **dialogs + Progress Window** instead of one custom window.

---

## Happy path

```mermaid
flowchart TD
  A([Double-click Web Audit.app]) --> B{URL provided?}
  B -->|droplet / argv| C[Validate https URL]
  B -->|no| D[Dialog: enter website address]
  D --> C
  C -->|invalid| E[Alert: paste full https URL]
  E --> D
  C -->|valid| F[Progress Window opens]
  F --> G[Run webaudit-docker · stream stdout to text view]
  G --> H{Success?}
  H -->|no| I[Alert: scan failed · log visible]
  I --> D
  H -->|yes| J[Alert: Report ready]
  J --> K[Open in browser]
  J --> L[Download / Show in Finder]
  J --> M[Scan another → D]
  K --> N([Safari · owner HTML report])
```

---

## Platypus UI mapping

```mermaid
flowchart LR
  subgraph platypus [Platypus built-in UI]
    P1[Text input dialog]
    P2[Progress Window + bar]
    P3[AppleScript display alert]
    P4[Notification optional]
  end

  subgraph mockup [HTML mockup file]
    M1[01-url-prompt.html]
    M2[02-progress.html]
    M3[03-complete.html]
    M4[04-error.html]
  end

  P1 --> M1
  P2 --> M2
  P3 --> M3
  P3 --> M4
```

---

## State model (script-side)

Not separate views — **one script run** per scan:

```text
1. Resolve URL (dialog or $1)
2. Open Progress Window (Platypus automatic when script runs)
3. echo progress · webaudit-docker streams -v output
4. osascript completion dialog
5. open report.html OR exit
```

Optional **second Platypus app** for Help only — usually overkill; menu link to GitHub doc is enough.

---

## Auto vs click

| Step | Automatic? |
|------|------------|
| Show Progress Window when script starts | Yes (Platypus) |
| Log scrolls as stdout arrives | Yes |
| Transition to “Report ready” dialog | Yes (script reaches osascript) |
| Open browser | User picks button on dialog |
| Help | User opens Help menu / OK on help dialog |

---

## Window spec

| Property | Platypus default / mockup |
|----------|---------------------------|
| Progress Window | ~520 × 380 px (adjust in Platypus.app) |
| Text view font | Menlo 11pt (matches `webaudit -v`) |
| Remain open after execution | **On** — so Jill can read log |
| Droplet mode | Optional — drag URL onto app icon |

---

## What Platypus cannot do (vs Swift)

- Custom branded single-window layout (dialogs only)
- Smooth in-window state animation
- App Store polish / ShareLink without shell hacks
- iPhone (macOS only — same as Swift desktop)

**Good enough for:** QA prototype, internal distribution, `.app` in Downloads before Swift v2.
