# Python construit les pages ; il n’est pas présent dans le conteneur qui les sert.
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f AS build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /build
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY quiz_data.py ./
COPY scripts/export_static.py ./scripts/export_static.py
COPY templates/ ./templates/
COPY static/ ./static/
COPY data/catalog.json ./data/catalog.json
COPY data/quizzes/ ./data/quizzes/
RUN python scripts/export_static.py

# Image officielle fixée par digest ; mettre à jour explicitement lors des reconstructions.
FROM caddy:2-alpine@sha256:6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b
# Le port 8000 n’exige aucune capacité réseau privilégiée.
RUN setcap -r /usr/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /build/dist/ /srv/
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8000/ || exit 1
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
