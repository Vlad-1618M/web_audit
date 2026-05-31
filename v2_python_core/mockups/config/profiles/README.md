# Framework extension profiles (mockups)

Auto-loaded when framework is detected or forced. Shipped in package as `webaudit/profiles/`.

| File | When loaded |
|------|-------------|
| [wordpress/plugins.example.yaml](wordpress/plugins.example.yaml) | `framework: wordpress` or auto-detect WP |
| [django/packages.example.yaml](django/packages.example.yaml) | Django detected |
| [laravel/packages.example.yaml](laravel/packages.example.yaml) | Laravel detected |
| [generic/php.example.yaml](generic/php.example.yaml) | Low confidence or `php` / `unknown` |

Site config `extensions:` block merges on top. See [docs/framework_profiles.md](../../docs/framework_profiles.md).
