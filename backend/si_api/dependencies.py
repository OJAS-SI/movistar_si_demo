"""Dependency wiring. The run store lives on the app, and routers receive it here,
so no module reaches for a global."""

from __future__ import annotations

from typing import Annotated, Mapping, Optional

from fastapi import Depends, Query, Request, WebSocket

from .i18n import catalogue_for
from .services.run_store import RunStore


def get_run_store(request: Request) -> RunStore:
    return request.app.state.run_store


def get_run_store_ws(websocket: WebSocket) -> RunStore:
    """The WebSocket equivalent: a WebSocket connection carries no Request."""
    return websocket.app.state.run_store


def get_catalogue(
    request: Request,
    lang: Optional[str] = Query(
        default=None,
        description="Language for operator-facing prose: 'en' or 'es'. Defaults to the "
                    "Accept-Language header, then English. Only the wording changes; "
                    "every number, id and code is identical in either language."),
) -> Mapping[str, str]:
    """The wording this request gets.

    An explicit ?lang wins, because the console's language toggle is a deliberate act;
    Accept-Language is the fallback, so a link opened by a Spanish-speaking colleague
    arrives in Spanish without anyone configuring anything. An unknown language falls
    back to English rather than erroring - see i18n.normalise_lang.
    """
    return catalogue_for(lang or request.headers.get("accept-language"))


def get_catalogue_ws(websocket: WebSocket, lang: Optional[str] = Query(default=None)
                     ) -> Mapping[str, str]:
    """The same choice for the live stream, which carries no Request."""
    return catalogue_for(lang or websocket.headers.get("accept-language"))


StoreDep = Annotated[RunStore, Depends(get_run_store)]
StoreWsDep = Annotated[RunStore, Depends(get_run_store_ws)]
CatalogueDep = Annotated[Mapping[str, str], Depends(get_catalogue)]
CatalogueWsDep = Annotated[Mapping[str, str], Depends(get_catalogue_ws)]