#!/usr/bin/env sh
# One-shot WordPress fixture for Web Audit integration tests.
# Profiles: weak | mid | good  (WEBAUDIT_WP_PROFILE / WP_PROFILE)
set -eu

PROFILE="${WEBAUDIT_WP_PROFILE:-${WP_PROFILE:-mid}}"
SITE_URL="${WP_URL:-http://localhost:8080}"

log() { printf '[wp-init] %s\n' "$*"; }

# wordpress (apache) creates wp-config on the shared volume; wp-cli must be able to patch it.
ensure_fs_writable() {
  log "Ensuring wp-config.php and wp-content are writable…"
  mkdir -p wp-content/uploads wp-content/plugins wp-content/themes
  if [ -f wp-config.php ]; then
    chmod 664 wp-config.php 2>/dev/null || chmod u+w wp-config.php 2>/dev/null || true
  fi
  chmod -R ug+rwX wp-content 2>/dev/null || chmod -R 777 wp-content 2>/dev/null || true
  if [ "$(id -u)" = 0 ]; then
    chown -R www-data:www-data wp-content 2>/dev/null || true
    [ -f wp-config.php ] && chown www-data:www-data wp-config.php 2>/dev/null || true
    chmod 664 wp-config.php 2>/dev/null || true
    chmod -R ug+rwX wp-content 2>/dev/null || true
  fi
}

log "profile=${PROFILE} url=${SITE_URL}"

cd /var/www/html

i=0
while [ "$i" -lt 90 ]; do
  if wp core version --allow-root >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 2
done

if ! wp core version --allow-root >/dev/null 2>&1; then
  log "ERROR: WordPress not ready after wait"
  exit 1
fi

ensure_fs_writable

if ! wp core is-installed --allow-root >/dev/null 2>&1; then
  log "Installing WordPress core…"
  wp core install \
    --url="$SITE_URL" \
    --title="WebAudit Test Site" \
    --admin_user=admin \
    --admin_password=password \
    --admin_email=admin@example.com \
    --skip-email \
    --allow-root
fi

log "Installing plugins (contact-form-7, wordpress-seo)…"
wp plugin install contact-form-7 wordpress-seo --activate --allow-root 2>/dev/null || true

log "Ensuring theme twentytwentyfour…"
wp theme install twentytwentyfour --activate --allow-root 2>/dev/null \
  || wp theme activate twentytwentyfour --allow-root 2>/dev/null || true

ensure_fs_writable

apply_profile() {
  case "$1" in
    weak|minimal)
      log "Profile weak — no DISALLOW_* hardening (file editor likely available)"
      wp config delete DISALLOW_FILE_EDIT --allow-root 2>/dev/null || true
      wp config delete DISALLOW_FILE_MODS --allow-root 2>/dev/null || true
      ;;
    mid|ok)
      log "Profile mid — DISALLOW_FILE_EDIT only"
      wp config set DISALLOW_FILE_EDIT true --raw --allow-root
      wp config delete DISALLOW_FILE_MODS --allow-root 2>/dev/null || true
      ;;
    good|strong)
      log "Profile good — DISALLOW_FILE_EDIT + DISALLOW_FILE_MODS + child theme"
      wp config set DISALLOW_FILE_EDIT true --raw --allow-root
      wp config set DISALLOW_FILE_MODS true --raw --allow-root
      if ! wp theme is-active webaudit-child --allow-root 2>/dev/null; then
        wp scaffold child-theme webaudit-child \
          --parent_theme=twentytwentyfour \
          --allow-root 2>/dev/null || true
        wp theme activate webaudit-child --allow-root 2>/dev/null || true
      fi
      ;;
    *)
      log "Unknown profile '$1' — using mid"
      wp config set DISALLOW_FILE_EDIT true --raw --allow-root
      wp config delete DISALLOW_FILE_MODS --allow-root 2>/dev/null || true
      ;;
  esac
}

apply_profile "$PROFILE"

log "Done — WordPress ready for external scans at ${SITE_URL}"
wp plugin list --allow-root 2>/dev/null | head -20 || true
wp theme list --allow-root 2>/dev/null | head -10 || true
