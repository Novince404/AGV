# syntax=docker/dockerfile:1

# Build the Vue application once and let the FastAPI container serve the
# immutable bundle. This keeps browser/API cookies same-origin in the standard
# trial deployment.
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim AS application
ARG AGV_VERSION=dev
LABEL org.opencontainers.image.title="AGV Dispatch System" \
      org.opencontainers.image.description="AGV v3 enterprise trial application" \
      org.opencontainers.image.version="${AGV_VERSION}" \
      org.opencontainers.image.licenses="PolyForm-Noncommercial-1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AGV_SERVE_FRONTEND_DIST=true \
    AGV_FRONTEND_DIST_DIR=/app/frontend/dist

RUN groupadd --system agv && useradd --system --gid agv --home-dir /app --create-home agv \
    && mkdir -p /app/data && chown -R agv:agv /app

WORKDIR /app/backend
COPY backend/requirements.lock ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.lock

COPY --chown=agv:agv backend/ /app/backend/
COPY --chown=agv:agv VERSION /app/VERSION
COPY --from=frontend-build --chown=agv:agv /build/frontend/dist /app/frontend/dist

USER agv
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/health/ready', timeout=3).status == 200"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
