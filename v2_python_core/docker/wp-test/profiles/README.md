# WordPress test profiles

Set via `WEBAUDIT_WP_PROFILE` or `WP_PROFILE` when starting the stack.

| Profile | Aliases | wp-config | Theme setup |
|---------|---------|-----------|-------------|
| **weak** | `minimal` | No `DISALLOW_*` constants | Parent theme only |
| **mid** | `ok` | `DISALLOW_FILE_EDIT` | Parent theme only |
| **good** | `strong` | Both `DISALLOW_FILE_EDIT` and `DISALLOW_FILE_MODS` | Child theme `webaudit-child` |

Web Audit **cannot read wp-config from outside** — these profiles let you compare scan output and manual verification on a local fixture.
