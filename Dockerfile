# Version exacte de la base auditée ; actualiser aussi ce digest lors des mises à jour.
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip==26.2.1 \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall --yes pip \
    && groupadd --system atelier \
    && useradd --system --gid atelier --no-create-home atelier

COPY app.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY data/questions.json ./data/questions.json

USER atelier

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).close()"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-server-header", "--no-access-log", "--limit-concurrency", "100", "--timeout-keep-alive", "5", "--timeout-graceful-shutdown", "10", "--backlog", "128"]
