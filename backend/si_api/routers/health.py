"""Liveness, and the versions that matter: the API's, the core's, and the frozen
four-field contract the core is built against."""

from __future__ import annotations

from fastapi import APIRouter

import si_core
from si_core.contracts import FROZEN_CONTRACT_VERSION

from ..schemas import HealthOut
from ..settings import API_VERSION

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Liveness and versions")
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        api_version=API_VERSION,
        core_version=si_core.__version__,
        frozen_contract_version=FROZEN_CONTRACT_VERSION,
    )