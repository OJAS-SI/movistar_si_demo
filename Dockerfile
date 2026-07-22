# Movistar Service Intelligence Twin — one image, one process, one port.
#
# The React console is built here rather than committed: frontend/dist is gitignored, and
# baking a stale bundle into the image is exactly the failure that makes a demo show old
# numbers. So the image builds the frontend from source and hands the result to FastAPI,
# which serves it alongside the API - the same single-process arrangement used locally.

# ---------- stage 1: build the console ----------
FROM node:22-alpine AS web

WORKDIR /build
# package files first: this layer is cached unless the dependencies actually change
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build          # tsc -b && vite build -> /build/dist


# ---------- stage 2: the runtime ----------
FROM python:3.13-slim AS runtime

# si_core is pure standard library and must stay that way; only the API layer has
# dependencies, and they are pinned in backend/requirements.txt.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=web /build/dist ./frontend/dist

# Not root. The app writes nothing to disk - runs are held in memory and rebuilt from
# their seed - so a read-only user is enough.
RUN useradd --create-home --uid 10001 si && chown -R si:si /app
USER si

# App Platform (and most PaaS) inject PORT; 8080 is the fallback for `docker run`.
ENV PORT=8080
EXPOSE 8080

# Prewarm both scales at boot so the scale toggle is instant. The server answers health
# checks immediately - prewarm is a background task - so this does not delay readiness.
ENV SI_PREWARM=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/api/health', timeout=4).status==200 else 1)"

# One worker on purpose. The run store is in-process memory: a second worker would hold
# its own copy of every run, so a client could create a run on one and 404 on the other.
CMD ["sh", "-c", "exec uvicorn si_api.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
