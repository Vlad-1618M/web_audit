# Web Audit v2 — Architecture Diagrams

*Mermaid diagrams using the same dark palette as [mockups/reports/shared-dark.css](../mockups/reports/shared-dark.css).*

**Browser preview:** open [mockups/diagrams/index.html](../mockups/diagrams/index.html) for rendered diagrams with glow styling.

---

## Theme (paste at top of any diagram block)

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'darkMode': true,
    'background': '#030306',
    'mainBkg': '#0e0e16',
    'secondBkg': '#14141f',
    'tertiaryColor': '#1a1a24',
    'primaryColor': '#0e0e16',
    'primaryTextColor': '#eef2ff',
    'primaryBorderColor': '#00f0ff',
    'secondaryColor': '#14141f',
    'secondaryTextColor': '#eef2ff',
    'secondaryBorderColor': '#ff0080',
    'tertiaryTextColor': '#8b95b0',
    'lineColor': '#8b95b0',
    'textColor': '#eef2ff',
    'nodeTextColor': '#eef2ff',
    'clusterBkg': '#14141f',
    'clusterBorder': '#00f0ff',
    'titleColor': '#00f0ff',
    'edgeLabelBackground': '#0e0e16',
    'pie1': '#ffc14d',
    'pie2': '#39ff8c',
    'pie3': '#a855f7',
    'pie4': '#00f0ff',
    'pieStrokeColor': '#030306',
    'pieLegendTextColor': '#eef2ff'
  }
}}%%
```

---

## 1. Pro v2 product focus

Primary job: **how safe and well-delivered** the public site is. SEO surface is informational only.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'darkMode': true,
    'background': '#030306',
    'pie1': '#ffc14d',
    'pie2': '#39ff8c',
    'pie3': '#a855f7',
    'pieStrokeColor': '#030306',
    'pieLegendTextColor': '#eef2ff',
    'titleColor': '#00f0ff'
  }
}}%%
pie title Pro v2 — where effort & scoring live
    "Hygiene — config & hardening" : 70
    "Exposure — leaks & secrets" : 25
    "SEO surface — INFO/VERIFY only" : 5
```

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'darkMode': true, 'background': '#030306', 'primaryColor': '#0e0e16', 'primaryTextColor': '#eef2ff', 'primaryBorderColor': '#00f0ff', 'lineColor': '#8b95b0', 'titleColor': '#00f0ff'}}}%%
flowchart LR
  subgraph PRIMARY["Primary — scored"]
    H["Hygiene / 100<br/><span style='color:#ffc14d'>headers · TLS · DNS · plugins</span>"]
    E["Exposure / 100<br/><span style='color:#39ff8c'>.env · .git · sensitive paths</span>"]
    V["Verdict<br/><span style='color:#00f0ff'>PASS · NEEDS ATTENTION · AT RISK</span>"]
  end
  subgraph SECONDARY["Secondary — not scored"]
    S["SEO_SURFACE<br/><span style='color:#a855f7'>INFO / VERIFY only</span>"]
  end
  H --> V
  E --> V
  S -.->|"no score impact"| V

  classDef hygiene fill:#0e0e16,stroke:#ffc14d,color:#eef2ff,stroke-width:2px
  classDef exposure fill:#0e0e16,stroke:#39ff8c,color:#eef2ff,stroke-width:2px
  classDef verdict fill:#0e0e16,stroke:#00f0ff,color:#eef2ff,stroke-width:2px
  classDef seo fill:#0e0e16,stroke:#a855f7,color:#eef2ff,stroke-width:2px
  class H hygiene
  class E exposure
  class V verdict
  class S seo
```

---

## 2. Tier stack

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'darkMode': true, 'background': '#030306', 'primaryColor': '#0e0e16', 'primaryTextColor': '#eef2ff', 'primaryBorderColor': '#00f0ff', 'secondaryBorderColor': '#ff0080', 'tertiaryColor': '#1a1a24', 'lineColor': '#8b95b0'}}}%%
flowchart TB
  T1["Tier 1 — Foundation<br/>HTTP · DNS · TLS · DOM · reports · PDF"]
  T2["Tier 2 — Depth<br/>JS · API · baselines · diff"]
  T2B["Tier 2b — WP plugins<br/>framework profiles · CVE cache"]
  T2C["Tier 2c — SEO surface<br/>INFO / VERIFY only"]
  T3["Tier 3 — Ecosystem<br/>SARIF · vuln snapshot · packaging"]

  T1 --> T2
  T2 --> T2B
  T2 --> T2C
  T2B --> T3
  T2C --> T3

  classDef t1 fill:#0e0e16,stroke:#00f0ff,color:#eef2ff,stroke-width:2px
  classDef t2 fill:#0e0e16,stroke:#ff0080,color:#eef2ff,stroke-width:2px
  classDef t2b fill:#0e0e16,stroke:#ffc14d,color:#eef2ff,stroke-width:2px
  classDef t2c fill:#0e0e16,stroke:#a855f7,color:#eef2ff,stroke-width:2px
  classDef t3 fill:#0e0e16,stroke:#39ff8c,color:#eef2ff,stroke-width:2px
  class T1 t1
  class T2 t2
  class T2B t2b
  class T2C t2c
  class T3 t3
```

---

## 3. Scan pipeline (config → collect → score → report)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'darkMode': true, 'background': '#030306', 'primaryColor': '#0e0e16', 'primaryTextColor': '#eef2ff', 'primaryBorderColor': '#00f0ff', 'clusterBkg': '#14141f', 'clusterBorder': '#00f0ff', 'lineColor': '#8b95b0'}}}%%
flowchart TB
  subgraph IN["Input"]
    CLI["CLI · typer"]
    CFG["YAML config"]
    SITE["Site profile"]
  end

  subgraph DETECT["Framework detect"]
    FW{"auto / forced"}
    PROF["profiles/{framework}/extensions.yaml"]
    GEN["profiles/generic/extensions.yaml"]
  end

  subgraph CORE["Python core"]
    COL["collectors/<br/>httpx · dnspython · tls"]
    AN["analyzers/<br/>policy · html · plugins · seo_surface"]
    SC["scoring/<br/>Hygiene · Exposure · Verdict"]
  end

  subgraph OUT["Output"]
    JSON["audit_run.json"]
    REN["render/ + templates/"]
    HTML["HTML · PDF · TXT"]
  end

  CLI --> COL
  CFG --> COL
  SITE --> COL
  FW -->|confidence OK| PROF
  FW -->|low confidence| GEN
  PROF --> COL
  GEN --> COL
  COL --> AN
  AN --> SC
  SC --> JSON
  JSON --> REN
  REN --> HTML

  classDef cyan fill:#0e0e16,stroke:#00f0ff,color:#eef2ff
  classDef magenta fill:#0e0e16,stroke:#ff0080,color:#eef2ff
  classDef gold fill:#0e0e16,stroke:#ffc14d,color:#eef2ff
  classDef lime fill:#0e0e16,stroke:#39ff8c,color:#eef2ff
  class CLI,CFG,SITE cyan
  class PROF,GEN magenta
  class COL,AN,SC gold
  class JSON,REN,HTML lime
```

---

## 4. Finding classes — what affects scores

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'darkMode': true, 'background': '#030306', 'primaryColor': '#0e0e16', 'primaryTextColor': '#eef2ff', 'lineColor': '#8b95b0'}}}%%
flowchart TD
  F["Raw finding"]
  F --> C{"Class?"}

  C -->|ACTION scored| H["−Hygiene points"]
  C -->|ACTION + sensitive path| X["−Exposure points"]
  C -->|VERIFY| V["Report only · confirm manually"]
  C -->|INFO| I["Report only"]
  C -->|EXPECTED| E["Normal for framework"]

  SEO["SEO_SURFACE checks"] --> I
  SEO --> V

  PLUGIN["Unauth CVE"] --> H
  PLUGIN --> X
  AUTHCVE["Auth-required CVE"] --> V

  classDef action fill:#0e0e16,stroke:#ff3355,color:#eef2ff,stroke-width:2px
  classDef verify fill:#0e0e16,stroke:#ffc14d,color:#eef2ff,stroke-width:2px
  classDef info fill:#0e0e16,stroke:#a855f7,color:#eef2ff,stroke-width:2px
  classDef ok fill:#0e0e16,stroke:#39ff8c,color:#eef2ff,stroke-width:2px
  class H,X action
  class V verify
  class I,SEO info
  class E ok
  class AUTHCVE verify
  class PLUGIN action
```

---

## 5. Framework profile resolution

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'darkMode': true, 'background': '#030306', 'primaryColor': '#0e0e16', 'primaryTextColor': '#eef2ff', 'primaryBorderColor': '#00f0ff', 'lineColor': '#8b95b0'}}}%%
sequenceDiagram
  participant U as User
  participant O as Orchestrator
  participant D as Framework detect
  participant P as Profile loader
  participant C as Collectors

  U->>O: webaudit scan URL
  O->>D: fingerprint headers/body/cookies
  alt WordPress confidence ≥ 0.65
    D->>P: load wordpress/extensions.yaml
  else Django / Laravel
    D->>P: load django|laravel profile
  else unknown
    D->>P: load generic/extensions.yaml
  end
  P->>O: merge site.extensions overrides
  O->>C: run enabled collectors only
  C-->>U: audit_run.json + reports
```

---

## Color reference (matches report mockups)

| Token | Hex | Use in diagrams |
|-------|-----|-----------------|
| Background | `#030306` | Canvas |
| Surface | `#0e0e16` | Node fill |
| Cyan | `#00f0ff` | Primary / Tier 1 / CLI |
| Magenta | `#ff0080` | Tier 2 / profiles |
| Gold | `#ffc14d` | Hygiene |
| Lime | `#39ff8c` | Exposure / output |
| Violet | `#a855f7` | SEO surface |
| Coral | `#ff3355` | ACTION / risk |

---

*Related: [architecture.md](architecture.md) · [seo_surface.md](seo_surface.md) · [stages.md](stages.md)*
