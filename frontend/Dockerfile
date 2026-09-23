# Static frontend served by Caddy (D-003). Built on Railway (no local Docker, D-014).
FROM caddy:2-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY index.html auth.html requests.html new.html request.html staff.html staff-request.html reviews.html admin.html /srv/
COPY css /srv/css
COPY js /srv/js
COPY fonts /srv/fonts

RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh \
 && rm -f /srv/js/config.js \
 && addgroup -S web && adduser -S -G web web \
 && touch /srv/js/config.js && chown web:web /srv/js/config.js

USER web
# Caddy state in the user's home (the base image's /data and /config volumes stay root-owned)
ENV PORT=8080 XDG_DATA_HOME=/home/web/.local/share XDG_CONFIG_HOME=/home/web/.config
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
