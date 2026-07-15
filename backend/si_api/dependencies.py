"""Dependency wiring. The run store lives on the app, and routers receive it here,
so no module reaches for a global."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, WebSocket

from .services.run_store import RunStore


def get_run_store(request: Request) -> RunStore:
    return request.app.state.run_store


def get_run_store_ws(websocket: WebSocket) -> RunStore:
    """The WebSocket equivalent: a WebSocket connection carries no Request."""
    return websocket.app.state.run_store


StoreDep = Annotated[RunStore, Depends(get_run_store)]
StoreWsDep = Annotated[RunStore, Depends(get_run_store_ws)]