# WordPress Theme Threat Model  - _web_audit v2_ 

## Research Purpose:
_Research compiled: June 2026_ <br>
**Threat model for WordPress theme-layer security checks in web_audit v2.**<br>

> **Implementation status (v2.1.0b3+):** Passive checks below are implemented — `collectors/wp_themes.py`, `analyzers/wp_themes.py`, Technical report **WordPress theme** section. Theme CVE via WPScan cache remains Stage 6 deferred.

__*Covers:*__
- Theme version staleness. <br>
- DISALLOW_FILE_EDIT exposure. <br> 
- Child theme detection. <br>
- Confirmed CVEs, real-world attack evidence, and passive detection logic.<br>
---

## 1. Is This Worth Including ?

**Yes. The value is real and the detection is achievable passively.** <br>
Themes are a lower-volume vulnerability source than plugins — in 2024, plugins
accounted for 96% of all WordPress vulnerabilities and themes for 4% — but that
framing is misleading in two ways:<br>
- First -  4% of 7,966 vulnerabilities is still roughly 320 theme CVEs in a single year.<br>
- Second -  Theme vulnerabilities are systematically under-researched. Themes are
generally less investigated than plugins, as they tend to be premium with no free
plans and their code is not as readily available to researchers. This means real
exposure is likely higher than reported numbers reflect.
- Third - and most important — the *behaviour pattern* around themes
(deliberate update freezing, direct file editing left open, no child theme) is
arguably more dangerous than any single CVE. <br> 
A site can be fully patched on plugins and still be sitting on a 3-year-old frozen theme with the file editor wide open.

**Optimistic benefit with this feature included:**
For users (non-technical site owners, agencies being audited), the theme
checks close a blind spot that almost every other tool ignores. Plugin scanners
are common. Theme staleness + editor exposure checks are rare. Adding this makes
web_audit practically unique for the audience described in the v2 README.<br>
**Without it:** - tool gives a false sense of completeness. A clean plugin
report on a site with Avada 7.11.6 (critical CVE, unauthenticated) or a frozen
Divi install with the file editor open is a missed threat.

---
## 2. Threat 1 - Stale / Frozen Theme Versions
### The Root Cause:
Developers intentionally disable theme auto-updates to protect their custom
modifications made directly to theme core files. <br> 
When a theme update ships, it would overwrite their changes, so they freeze the version.<br> 
The site then runs an increasingly outdated theme indefinitely.

> This is "Shadow IT" in the WordPress world: <br> A local development shortcut that permanently compromises production security.

### Real-World Evidence
Approximately 35% of all WordPress vulnerabilities disclosed in 2024
remained unpatched in 2025, leaving over one-third of known flaws with no
security update applied — with deletion as the only safe option for site owners.<br>
In late 2025, a critical flaw in a widely used plugin had 4,500+ attacks
blocked in just the first day of disclosure. Sites that updated in time were safe;
those that did not were not.<br> 
The same dynamic applies to themes. The window between disclosure and active exploitation is now measured in hours, not weeks.

### Confirmed Theme CVEs (2023–2026)

| Theme | Affected Version | CVE | Type | Auth | Severity | Patched In | Date |
|---|---|---|---|---|---|---|---|
| Avada | ≤ 7.11.13 | CVE-2024-13346 | Unauthenticated Shortcode Exec / SSRF chain | None | Critical (9.2) | 7.11.14 | 2024 |
| Avada | 7.0–7.11.6 | — | Local File Inclusion / Sensitive Data Exposure | None | High (7.1) | 7.11.7 | Apr 2024 |
| Avada | ≤ 7.11.6 | — | Sensitive Info Exposure via fusion-forms dir | None | Medium | 7.11.7 | Apr 2024 |
| Avada Builder plugin | — | CVE-2023-39307 | Contributor+ Arbitrary File Upload / RCE | Contributor | Critical | — | 2023 |
| Avada Builder plugin | — | CVE-2023-39309 | Authenticated SQL Injection | Authenticated | Critical | 3.11.2 | 2023 |
| Avada Builder plugin | — | CVE-2023-39306 | Reflected XSS | None | High | 3.11.2 | 2023 |
| Divi | 4.0–4.24.2 | CVE-2024-38291 | CSRF — unauthorized admin actions | Social eng. | Medium (6.8) | 4.24.3 | 2024 |
| Divi | ≤ 4.25.0 | — | Authenticated Contributor DOM-based Stored XSS | Contributor | Low | 4.25.1 | 2025 |
| Motors | ≤ 5.6.81 | CVE-2025-64374 | Missing permission check on AJAX plugin install | Subscriber | Critical | — | Dec 2025 |
| Alone (theme) | ≤ 7.8.3 | CVE-2025-5394 | Arbitrary File Upload / RCE via plugin install | None | Critical (9.8) | 7.8.5 | Jun 2025 |
| DWT Directory & Listing | ≤ 3.3.3 | CVE-2025-0215 | Reflected XSS | None | Medium (6.1) | — | Jan 2025 |
| BlogMarks | — | CVE-2025-6247 | Local File Inclusion | None | High | No fix | Aug 2025 |
| Eximious Magazine | — | CVE-2025-53247 | Local File Inclusion | None | High | No fix | Aug 2025 |
| Glamer | — | CVE-2025-53248 | Local File Inclusion | None | High | No fix | Aug 2025 |
| Magazine Elite | — | CVE-2025-53216 | Local File Inclusion | None | High | No fix | Aug 2025 |

### The Avada Case — Confirmed Mass Exploitation
CVE-2024-13346 affects the Avada Website Builder for WordPress and
WooCommerce (versions up to and including 7.11.13), allowing unauthenticated
arbitrary shortcode execution via improperly validated input. Researchers chained
this into broader exploits including sensitive data exposure, a potential blind
SSRF callback, and XSS via plugin chaining.

Avada, with over 875,000 sales, contained a local file inclusion vulnerability
that allowed authenticated attackers to read arbitrary files from the web server,
including database credentials and API keys.

### The Alone Theme — Actively Exploited Before Disclosure

CVE-2025-5394 began to be exploited starting July 12, two days before the
vulnerability was publicly disclosed — indicating threat actors were actively
monitoring code changes for newly addressed vulnerabilities. Wordfence blocked
120,900 exploit attempts targeting the flaw. In observed attacks, the vulnerability
was used to upload ZIP archives containing PHP-based backdoors to execute remote
commands and upload additional files.

### The Motors Theme — Site Takeover via Subscriber Account

A critical flaw in the Motors WordPress theme, affecting more than 20,000
installations, allows low-privileged users to gain full control of websites. While
the function uses a nonce for request validation, it lacks a proper permission check.
Because the nonce value can be accessed by Subscriber-level users, any logged-in
user can supply an arbitrary plugin URL, upload and activate malicious plugins,
and achieve a full site takeover.

---

## 3. Threat 2 — DISALLOW_FILE_EDIT Missing in Production

### What It Is:
WordPress ships with a built-in Theme File Editor and Plugin File Editor accessible
from the admin dashboard (Appearance > Theme File Editor). <br>
Any administrator can edit live PHP files directly from the browser. Setting `define('DISALLOW_FILE_EDIT', true)` in `wp-config.php` disables this editor for all users including admins.
The constant is not set by default. Most WordPress installations ship with the
editor active.

### The Attack Chain Without This Constant

The attacker logs in to /wp-admin as a real admin user. From WordPress's
perspective, nothing is wrong — this is a legitimate login. The attacker walks
straight to Appearance > Theme File Editor, opens functions.php, and pastes a
small PHP backdoor at the top. From that moment on, every request to the front
page of the site executes the attacker's code. They have a remote shell on the
server. The editor turns "stolen admin password" into "stolen webserver".

Without the editor, an attacker who steals an admin password still has admin
access (bad enough), but they have to take the slower, noisier route of uploading
a malicious plugin or theme zip to get code execution. That extra step is one more
chance for a security plugin, a file integrity scanner, or a server-level WAF to
notice and block the upload.

### Who Gets Hit by This

The most common WordPress hack path is a stolen or brute-forced admin password,
not a zero-day exploit. Once an attacker has admin access, installing a malicious
plugin is the fastest way to establish a persistent backdoor.<br> 
With DISALLOW_FILE_MODS enabled, even a compromised admin account cannot install plugins, upload themes, or edit PHP files through the WordPress interface.

This is not a theoretical risk. It is the standard escalation path on every
credential compromise, phishing attack, or session hijack that lands on an
admin account.

### The Companion Constant

`DISALLOW_FILE_EDIT` disables the editor only.<br>
`DISALLOW_FILE_MODS` goes further — it also blocks plugin/theme installation and
updates via the dashboard.<br> 
A site with both constants set is significantly harder to pivot on even after a full admin credential compromise.

### WordPress's Own Acknowledgment

WordPress core itself has a CVE (BIT-wordpress-2024-31210) that involves the
interaction between `DISALLOW_FILE_EDIT` and FTP credential prompts.<br> 
If the DISALLOW_FILE_EDIT constant is set to true and FTP credentials are required when
uploading a new theme or plugin, this technically allows RCE when the user would
otherwise have no means of executing arbitrary PHP code.<br>
Sites where the DISALLOW_FILE_MODS constant is set to true are not affected.<br> 
WordPress acknowledges the constant as an intentional hardening tool in its own security
documentation.

---

## 4. Threat 3 - Missing Child Theme (Update Trap Detection)

### The Pattern:

- Good practice: - make all customizations in a Child Theme. <br>
The child overrides specific files; the parent theme updates cleanly on its own. <br> 
The child is never touched by parent updates.

- Bad practice (extremely common): -  modify core parent theme files directly. <br>
Now every theme update would overwrite your changes.<br>
Solution chosen by most agency devs: - Disable theme updates forever.<br>
The site is now permanently frozen on whatever version was current at project handoff.

### Why This Matters for web_oudit Tool ?

- A site with no child theme + a heavily modified popular parent theme (Avada,
Divi, OceanWP, Astra, GeneratePress) is almost certainly in the "never update"
loop. <br>
It is a soft indicator, not a confirmed vulnerability — but combined with
a stale version number, it becomes a high-confidence signal.

- InspectWP explicitly distinguishes between parent and child theme and shows
both in a report when present — allowing you to immediately see whether a site
has custom adjustments via a child theme. <br> 
This detection method is established and works passively from page source.

---

## 5. Passive Detection Logic for web_audit

### What Is Detectable Without Auth (External Scan)

All of the following are publicly accessible on a standard WordPress installation:

```
wp-content/themes/<slug>/style.css
  → Theme Name, Version, Template (parent theme), Author, Description

wp-content/themes/<slug>/readme.txt  (sometimes present)
  → Version, changelog

HTML source:
  → /wp-content/themes/<slug>/ paths identify active theme slug
  → If Template: <parent-slug> exists in style.css, site is using a child theme
  → Absence of Template field on a heavily modified popular theme = parent-only risk

wp-content/themes/<slug>/style.css Template field:
  → Present  → child theme confirmed
  → Absent   → parent theme being used directly
```

`DISALLOW_FILE_EDIT` status cannot be confirmed from outside (it is a PHP constant
in wp-config.php). However, its *absence* can be inferred indirectly:

- If the WordPress admin login page is reachable (default: /wp-login.php or /wp-admin)
  → flag that file editor is likely exposed unless hardening is confirmed
- The check should be reported as: "Cannot confirm DISALLOW_FILE_EDIT is set.
  This is a known critical hardening constant. Manual verification required."

### Detection Algorithm

```
Step 1. Identify active theme slug
        - Pattern: /wp-content/themes/<slug>/ in page source HTML

Step 2. Fetch style.css
        GET https://<target>/wp-content/themes/<slug>/style.css
        Parse header fields:
          Theme Name:
          Version:
          Template:        ← if present, site uses child theme
          Author:
          Author URI:

Step 3. Resolve current version
        For themes on wordpress.org (free themes):
          GET https://api.wordpress.org/themes/info/1.1/?action=theme_information
              &request[slug]=<slug>&request[fields][version]=true
        For premium themes (Avada, Divi, etc.):
          Maintain static lookup table — versions not available via WP API
          Compare against known-vulnerable version table (WPScan DB)

Step 4. Resolve known vulnerabilities
        WPScan API:
          GET https://wpscan.com/api/v3/themes/<slug>
        Patchstack API (secondary)

Step 5. Child theme check
        If style.css contains "Template: <parent-slug>" → child theme confirmed
        If not → flag parent-direct pattern
        If parent-direct AND parent is a well-known premium theme
          (Avada, Divi, Astra, OceanWP, GeneratePress, Flatsome, Neve, etc.)
          → raise "Update Trap Warning"

Step 6. DISALLOW_FILE_EDIT check
        Cannot be confirmed externally
        Flag as: "Editor status unverifiable — medium risk assumption"
        Log: admin panel reachability (/wp-admin, /wp-login.php)
        If admin panel is open + no other hardening signals → elevate to HIGH
```

### Flag Conditions

```
Theme version current                       → PASS
Theme 1 minor version behind               → LOW  (informational)
Theme 2–3 minor versions behind            → MEDIUM
Theme 1+ major versions behind             → HIGH (likely frozen)
Theme version matches known CVE            → HIGH / CRITICAL (per CVSS)
Theme not on wordpress.org (premium/custom)→ INFO + manual CVE check recommended
No version string in style.css             → SUSPICIOUS (version stripped/hidden)
style.css Template field present           → PASS (child theme in use)
style.css Template field absent on popular → WARNING (update trap likely)
  premium parent theme
DISALLOW_FILE_EDIT unverifiable            → MEDIUM (manual review required)
Admin panel publicly accessible            → elevate file editor risk to HIGH
```

---

## 6. Scoring Integration (Hygiene vs Exposure Axes)

| Condition | Hygiene Impact | Exposure Impact |
|---|---|---|
| Theme current | None | None |
| 1 minor stale | Low negative | None |
| 2–3 minors stale | Medium negative | Low |
| Major version behind | High negative | Medium |
| Matches CVE (medium) | High negative | Medium |
| Matches CVE (critical) | Critical | Critical |
| No version detectable | Medium negative | Medium |
| No child theme on popular parent | Warning | Low (update trap signal) |
| DISALLOW_FILE_EDIT unverifiable | Medium negative | Medium |
| Admin panel open + editor likely active | High negative | High |

### Version-Sync Thresholds (Theme-Specific)

Themes tend to have fewer releases than plugins. Calibrate accordingly:

| Gap | Label | Score Impact |
|---|---|---|
| Current | Clean | 0 |
| 1 minor behind | Stale | -5 |
| 2–3 minors behind | Neglected | -15 |
| 6+ months since last update | Likely frozen | -20 |
| 12+ months since last update | Abandoned / frozen | -30 |
| 1+ major version behind | Critical neglect | -35 |
| Matches CVE entry | Confirmed exposure | Per CVSS; flag Exposure axis |

---

## 7. Commonly Frozen Premium Themes (High-Value Detection Targets)

These are the most widely deployed premium themes that consistently appear in
frozen / stale configurations on client-owned sites:

| Theme | Active Installs / Sales | Known CVE History | Notes |
|---|---|---|---|
| Avada | 875,000+ sales | Yes — multiple critical | Most popular premium theme; active CVE history |
| Divi (Elegant Themes) | 1M+ installs | Yes — CSRF, XSS | CSRF CVE 2024; XSS 2025 |
| OceanWP | 700,000+ | Yes | Widely nulled; often frozen |
| Astra | 2M+ | Yes — XSS | High volume; frequently outdated |
| GeneratePress | 400,000+ | Yes | Lighter codebase; fewer CVEs |
| Flatsome | WooCommerce staple | Yes | Popular for ecommerce; update avoidance common |
| Neve | 100,000+ | Yes | Fast-growth theme; CVEs disclosed 2024 |
| Hello (Elementor default) | 5M+ | Low | Minimal; but Elementor Pro CVEs are the real risk |
| Blocksy | 100,000+ | Yes — XSS | Growing install base; less scrutinized |
| Motors | 20,000+ | CVE-2025-64374 (Critical) | Subscriber-level full site takeover |

---

## 8. Data Sources

| Source | Type | Cost | Notes |
|---|---|---|---|
| wordpress.org/themes/info API | Latest version, last updated | Free, no auth | Works for free/repo themes only |
| wpscan.com API v3 /themes/<slug> | CVE lookup per theme slug | Free (25/day) | Covers premium themes too |
| Patchstack DB | CVE feed | Free tier | Good secondary; active research program |
| Wordfence Intelligence | CVE feed + exploitability flags | Free read | High quality; marks actively exploited |
| NVD / NIST | Raw CVE data | Free | Authoritative; less WP-specific |
| style.css Template field | Child theme detection | No cost; passive | Direct from target site |

---

## 9. What WordPress Has Publicly Admitted

WordPress.org maintains a formal security disclosure process and has acknowledged
theme-layer risks in the following ways:

- The `DISALLOW_FILE_EDIT` constant is documented in the official WordPress
  Hardening Guide as a required production setting. Its absence is treated as
  a known misconfiguration, not an edge case.
- WordPress itself received CVE-2024-31210 related to how the constant interacts
  with FTP credential prompts — confirming the company tracks and acknowledges
  risks in this layer.
- The WordPress Vulnerability Database (via Wordfence Intelligence) publicly
  lists theme CVEs with exploitability status, confirming active exploitation
  on themes like Avada, Motors, and Alone in 2024–2025.
- Patchstack's 2025 mid-year report — cited in WordPress security communications
  — acknowledged that theme vulnerabilities are growing as more premium theme
  developers join the responsible disclosure program, confirming the research
  gap was structural, not because themes were safe.

No single mass event equivalent to a core WordPress breach has been publicly
attributed to themes alone. However, the Alone theme exploitation (120,900
blocked attempts, pre-disclosure exploitation) and the Avada CVE chain (SSRF,
PII exposure, XSS from a single entry point) are the closest documented cases.

---

## 10. Summary — Should web_audit Include This?

| Check | Include? | Detection Method | Effort |
|---|---|---|---|
| Theme version staleness | Yes | style.css + WP API | Low |
| Theme CVE match | Yes | WPScan API | Low (same code path as plugins) |
| Child theme detection | Yes | style.css Template field | Very Low |
| Update trap warning (parent-direct) | Yes | slug + Template field logic | Low |
| DISALLOW_FILE_EDIT missing | Yes (partial) | Cannot confirm; flag as advisory | Low |
| Admin panel open (editor escalation) | Yes | HTTP probe /wp-admin | Very Low |

**All six checks are achievable passively. <br>
The theme detection code path is almost identical to the plugin detection path already in beta. The marginal implementation cost is low. The coverage gap it closes is significant.**

---

*Planning document — web_audit v2 | Author: Vlad | Last updated: June 2026*
