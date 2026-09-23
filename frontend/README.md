# Frontend — ראיות צמחים

Static Hebrew RTL site: HTML + CSS + ES modules, no build step. See `docs/architecture.md` → Frontend.

## Run locally
```
cp frontend/.env.example frontend/.env     # public values only: API_BASE_URL=http://localhost:8000, SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY
python frontend/dev_server.py              # http://localhost:8080
```
The backend must allow the origin (`CORS_ALLOWED_ORIGINS=http://localhost:8080`), and the Supabase project's Auth → URL Configuration must include `http://localhost:8080/**` as a redirect URL (verification and reset links).

## Container (Railway)
`Dockerfile` (caddy:2-alpine, non-root). Env: `PORT`, `APP_ENV` (`dev|production`), `API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`. `docker-entrypoint.sh` validates them and writes `/srv/js/config.js`; the CSP `connect-src` is built from the same values in the `Caddyfile`.

## Vendored files
| File | Source | SHA-256 |
|------|--------|---------|
| `js/vendor/supabase.js` | `@supabase/supabase-js@2.117.0` `dist/umd/supabase.js` (jsDelivr) | `7b9e9c64109e15c338fa58c2bc77c32fb1c459bd587e22fc6b72cca80a388645` |
| `fonts/NotoSansHebrew-hebrew.woff2` | Google Fonts, Noto Sans Hebrew v50 (OFL), hebrew subset | `8dd0a0bc744eca2c6d5d618bf002f8ef98b2948b31020e3cb64fe3587c9abb74` |
| `fonts/NotoSansHebrew-latin.woff2` | same, latin subset | `27fd789f4089b6aa76494638b3f94a6c00c69a0519e38add75a3c7e852cab1bc` |

## Rules
- Never `innerHTML` / `insertAdjacentHTML`: build nodes with `h()` from `js/dom.js`.
- No inline `<script>` or `style=`: the CSP forbids them.
- Users never see drafts, internal status, job errors, ETA or queue position.
