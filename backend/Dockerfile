FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app

RUN useradd --create-home appuser
USER appuser
# Railway injects PORT. Rate limiting keys on X-Real-IP (set by Railway's edge) — verify in Phase 5.
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
