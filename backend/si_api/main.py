"""
The application factory.

Layering, stated once and enforced by imports:

    si_core   the domain. Pure standard library, frozen four-field contract, knows
              nothing about HTTP, Pydantic, or the web. It does not import si_api.
    si_api    this layer. Owns transport: schemas, routes, sockets, errors. It is the
              only thing allowed to import si_core, and it maps domain to wire in
              exactly one place (serializers.py).
    frontend  React. Speaks only to si_api, over the schemas in schemas.py.

Run it:
    uvicorn si_api.main:app --reload --app-dir backend
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import health, runs, stream
from .services.run_store import RunNotFound, RunNotReady, RunStore
from .settings import API_VERSION, Settings, get_settings

DESCRIPTION = """
Structural Intelligence for predictive fault localization on an IPTV and fixed-broadband
access network, on a 100% synthetic, fault-injected model of a Telefonica-style Spanish
network. No Telefonica data.

The engine reads only four fields per entity - `entity_src`, `entity_dst`, `timestamp`,
`magnitude` - and from that alone detects a forming fault, names the element responsible,
places it in its true layer, and recommends the action, with a certified-decision receipt.

Start with `POST /api/runs`, then read `GET /api/runs/{run_id}/console`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    app.state.settings = settings
    app.state.run_store = RunStore(max_runs=settings.max_runs)
    yield
    app.state.run_store = None


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Movistar Service Intelligence API",
        description=DESCRIPTION,
        version=API_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----- domain errors, mapped to HTTP once, here -----

    @app.exception_handler(RunNotFound)
    async def _run_not_found(request: Request, exc: RunNotFound) -> JSONResponse:
        return JSONResponse(status_code=404,
                            content={"detail": f"No run {exc.args[0]!r}. It never existed, "
                                               f"or it has been evicted from the store."})

    @app.exception_handler(RunNotReady)
    async def _run_not_ready(request: Request, exc: RunNotReady) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    # ----- the API -----

    app.include_router(health.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    app.include_router(stream.router, prefix="/api")

    # ----- the built frontend, when there is one -----

    if settings.serve_frontend:
        dist = settings.frontend_dist
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str) -> FileResponse:
            """Serve the React app, and let it own its own routing."""
            candidate = dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()