# Web Audit v2 — in plain English

*For site owners, PMs, or anyone who does not live in a terminal. Developers: see [README](../README.md) for the technical quick start.*

---

## What is Web Audit?

Web Audit looks at your **public website** the way a stranger on the internet would — and tells you, in simple scores, whether basic security hygiene looks okay or needs work.

It is **not** a full penetration test. It is a **health check**: headers, DNS email protection, and (as v2 grows) TLS, exposed files, and more.

You type a command with your site URL. You get a short summary and a saved report file you can open or send to your developer.

---

## “Installing” the tool — what that actually means

When a developer runs setup (for example `./dev-venv.sh setup` or `pip install`), they are **putting the Web Audit program on the computer** so the command `webaudit` works.

Think of it like installing an app on your phone:

| Step | Plain English |
|------|----------------|
| **Setup / pip install** | The app is installed. You can open it (run `webaudit scan …`). |
| **Virtual environment (`.venv`)** | A small, separate toolbox used only for this project — so it does not clash with other Python projects on the same machine. |
| **`webaudit scan https://yoursite.com`** | Run a check on that site. Results are saved under `audit_logs/`. |

**Important:** Until someone runs setup on that machine, `webaudit` will not work there. It is not automatic for every user on the internet — it runs from **your** computer (or your CI server) with **your** permission to test the site.

---

## What `webaudit completion install` means (and what it does *not* mean)

Recommended command (replaces the older `--install-completion` flag):

```bash
webaudit completion install
```

You will see a plain-English panel explaining what changed on your system.

### What it does **not** mean

- It does **not** install Web Audit again.
- It does **not** put the tool “inside the shell” as a permanent system module.
- It does **not** change your website or server in any way.
- It is **optional** — scans work fine without it.
- **Deleting `.venv` does not remove Tab completion** — completion lives in your home folder (see below).

### What it **does** mean

It adds a **small file in your home directory** so the terminal can suggest commands when you press **Tab** (like autocomplete on a phone keyboard).

| Shell | Typical file location |
|-------|------------------------|
| zsh (macOS default) | `~/.zfunc/_webaudit` |
| bash | `~/.bash_completions/webaudit.sh` |
| fish | `~/.config/fish/completions/webaudit.fish |

After you restart the terminal (or open a new window):

- Type `webaudit ` and press **Tab** → the shell may suggest `scan`, `completion`, etc.
- Type `webaudit scan --` and press **Tab** → it may suggest flags like `--json`.

### Check status

```bash
webaudit completion status
```

Shows whether those files exist and reminds you that `.venv` and completion are separate.

### Uninstall Tab completion only

```bash
webaudit completion uninstall
```

Removes the autocomplete file(s) from your home directory. **The `webaudit` command itself stays installed** until you remove the Python venv (`./dev-venv.sh teardown` or delete `.venv`).

### Remove the tool entirely (not the same as completion uninstall)

| Goal | What to run |
|------|-------------|
| Stop Tab suggestions only | `webaudit completion uninstall` |
| Remove Web Audit from this machine | `./dev-venv.sh teardown` or delete `v2_python_core/.venv` |

That is all. Tab completion is a **convenience for people who type commands often**, not a requirement to use the product.

---

## Running a scan — what you will see

Example:

```bash
webaudit scan https://example.com
```

Typical output:

| Line | Meaning |
|------|---------|
| **Hygiene** (0–100) | How well the site is configured (headers, DNS, etc.). Higher is better. |
| **Exposure** (0–100) | Whether sensitive files look reachable from outside. 100 = nothing obvious leaked. |
| **Verdict** | Plain label: **PASS**, **NEEDS_ATTENTION**, or **AT_RISK**. |
| **Findings** | Count of individual checks (missing header, missing DMARC, etc.). |

The full detail is in a JSON file:

```text
audit_logs/<date>_<your-site>/audit_run.json
```

Your developer can turn that into an HTML report as v2 matures. Mockups of those reports are in [mockups/reports/](../mockups/reports/).

---

## Help commands

| Command | Works? | Notes |
|---------|--------|-------|
| `webaudit --help` | Yes | Full list of commands |
| `webaudit -h` | Yes | Same as `--help` |
| `webaudit scan --help` | Yes | Options for a scan |

---

## Who does what

| Role | Typical action |
|------|----------------|
| **Site owner** | Ask for a scan; read Verdict + Hygiene/Exposure; share `audit_run.json` or future PDF with your dev. |
| **Developer / agency** | Run setup once, run scans in CI or locally, fix ACTION items in the report. |
| **You (dev on this repo)** | Use `./dev-venv.sh` to create/remove the local toolbox; run `pytest` before changes. |

---

## One-sentence summary

**Setup installs the checker; `scan` runs the checker on a URL; `--install-completion` only makes Tab-key suggestions in the terminal — nothing more.**
