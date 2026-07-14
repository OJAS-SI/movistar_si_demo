"""
Module 0 - Deterministic seeding.

Every run of the demo must be exactly reproducible: the same seed produces the
same synthetic network, the same telemetry, the same injected faults, and hence
the same scores. This module provides SeededRandom, a thin wrapper over the
standard library's random.Random, plus a mechanism for deriving independent named
child streams from one master seed.

Why child streams matter: the topology generator, the telemetry generator, and
the fault-injection engine each need randomness, but they must not consume from a
single shared stream, or the order in which they happen to draw would couple them
and make a change in one perturb the others. Instead each module asks the master
SeededRandom for a named child (e.g. "topology", "telemetry", "faults"), and each
child is a deterministic function of the master seed and the name. Reordering or
adding modules then never disturbs another module's sequence.
"""

from __future__ import annotations

import hashlib
import random
from typing import List, Sequence, TypeVar

T = TypeVar("T")


def _derive_seed(master_seed: int, name: str) -> int:
    """Derive a stable 64-bit child seed from a master seed and a stream name.
    Uses SHA-256 so the derivation is deterministic across platforms and Python
    runs (unlike hash(), which is salted)."""
    digest = hashlib.sha256(f"{int(master_seed)}::{name}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


class SeededRandom:
    """A reproducible random source. Wraps random.Random so the demo never touches
    global random state, and exposes child() for deriving independent named streams."""

    def __init__(self, seed: int, name: str = "master") -> None:
        self._seed = int(seed)
        self._name = name
        self._rng = random.Random(self._seed)

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def name(self) -> str:
        return self._name

    def child(self, name: str) -> "SeededRandom":
        """Return an independent SeededRandom for the named sub-stream, derived
        deterministically from this stream's seed and the name."""
        return SeededRandom(_derive_seed(self._seed, name), name=f"{self._name}/{name}")

    # --- thin, explicit pass-throughs (kept minimal and named for clarity) ---

    def random(self) -> float:
        """Uniform float in [0, 1)."""
        return self._rng.random()

    def uniform(self, low: float, high: float) -> float:
        return self._rng.uniform(low, high)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._rng.gauss(mu, sigma)

    def randint(self, low: int, high: int) -> int:
        """Inclusive integer in [low, high]."""
        return self._rng.randint(low, high)

    def choice(self, seq: Sequence[T]) -> T:
        return self._rng.choice(seq)

    def sample(self, population: Sequence[T], k: int) -> List[T]:
        return self._rng.sample(list(population), k)

    def shuffle(self, seq: List[T]) -> None:
        self._rng.shuffle(seq)

    def __repr__(self) -> str:
        return f"SeededRandom(seed={self._seed}, name={self._name!r})"
