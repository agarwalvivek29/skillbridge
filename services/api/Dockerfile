# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION Dockerfile — api
#
# For local development with hot-reload, use Dockerfile.dev instead.
#
# Choose ONE language section and delete the others.
# Then remove api / api placeholders.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS production
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
RUN pip install uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev
COPY src/ ./src/
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uv", "run", "python", "-m", "api"]

