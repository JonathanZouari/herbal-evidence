#!/bin/sh
# Writes the PUBLIC runtime config and starts Caddy. Fails fast on missing/malformed values so a bad deploy
# never serves a broken or injectable config.js.
set -eu

url_re='^https?://[A-Za-z0-9.-]+(:[0-9]+)?$'
check() { printf '%s' "$2" | grep -Eq "$3" || { echo "invalid or missing $1" >&2; exit 1; }; }

check API_BASE_URL "${API_BASE_URL:-}" "$url_re"
check SUPABASE_URL "${SUPABASE_URL:-}" "$url_re"
check SUPABASE_PUBLISHABLE_KEY "${SUPABASE_PUBLISHABLE_KEY:-}" '^[A-Za-z0-9_.-]+$'
check APP_ENV "${APP_ENV:-}" '^(dev|production)$'

printf 'window.APP_CONFIG = Object.freeze({"APP_ENV":"%s","API_BASE_URL":"%s","SUPABASE_URL":"%s","SUPABASE_PUBLISHABLE_KEY":"%s"});\n' \
  "$APP_ENV" "$API_BASE_URL" "$SUPABASE_URL" "$SUPABASE_PUBLISHABLE_KEY" > /srv/js/config.js

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
