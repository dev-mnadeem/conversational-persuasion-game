# syntax=docker/dockerfile:1

# --- build: resolve dependencies into a wheel cache -----------------------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- runtime --------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOORMAN_PROVIDER=local \
    DOORMAN_SESSIONS_DIR=/var/lib/doorman/sessions

COPY --from=builder /install /usr/local

RUN useradd --system --create-home --uid 10001 doorman \
    && mkdir -p /var/lib/doorman/sessions \
    && chown -R doorman:doorman /var/lib/doorman

WORKDIR /app
COPY --chown=doorman:doorman app ./app

USER doorman
EXPOSE 7321

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7321/healthz').read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7321"]
