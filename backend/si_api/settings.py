"""Server settings, driven by the environment with demo-friendly defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Tuple

API_VERSION = "1.0.0"

# The repository root, from backend/si_api/settings.py.
REPO_ROOT = Path(__file__).resolve().parents[2]

# Vite's dev server, where the React app lives while you are working on it.
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


@dataclass(frozen=True)
class Settings:
    cors_origins: Tuple[str, ...] = DEFAULT_CORS_ORIGINS
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"
    max_runs: int = 16

    @property
    def serve_frontend(self) -> bool:
        """In production the API also serves the built React app, so the whole demo is
        one process on one port. In development Vite serves it and proxies here."""
        return (self.frontend_dist / "index.html").is_file()


@lru_cache
def get_settings() -> Settings:
    origins = os.environ.get("SI_CORS_ORIGINS")
    return Settings(
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip())
        if origins else DEFAULT_CORS_ORIGINS,
        max_runs=int(os.environ.get("SI_MAX_RUNS", "16")),
    )