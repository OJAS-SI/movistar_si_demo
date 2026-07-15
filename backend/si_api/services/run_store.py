"""
The run store: the API's only piece of state.

A run is CPU-bound and fully deterministic from its config, so the store does two
things. It executes the run off the event loop (in a worker thread, so a full-scale
run cannot stall the server), and it holds the finished DemoResult in memory so the
console, the scorecard, and the topology can all be served from one execution rather
than recomputed per request.

The store is in-memory and bounded. This is a demo, not a system of record: restart
the server and the runs are gone, which is fine, because the same scale and seed
reproduce the identical run.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional

from starlette.concurrency import run_in_threadpool

from si_core.contracts import DemoConfig
from si_core.orchestrator import DemoResult, config_for_scale, run_demo

# How many finished runs to keep. Full-scale results are large; the oldest is evicted.
MAX_RUNS = 16


@dataclass
class Run:
    """One execution of the pipeline, and whatever it has produced so far."""
    run_id: str
    scale: str
    config: DemoConfig
    status: str                      # "running" | "complete" | "failed"
    created_at: float
    result: Optional[DemoResult] = None
    error: Optional[str] = None
    _done: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    @property
    def seed(self) -> int:
        return self.config.seed

    @property
    def passed(self) -> Optional[bool]:
        return self.result.passed() if self.result else None

    @property
    def summary(self) -> Optional[str]:
        return self.result.summary() if self.result else None

    @property
    def runtime_seconds(self) -> Optional[float]:
        return self.result.runtime_seconds if self.result else None

    async def wait(self, timeout: Optional[float] = None) -> None:
        """Block until the run finishes (or the timeout elapses). Lets a client that
        wants the answer, not a poll loop, simply ask for it."""
        await asyncio.wait_for(self._done.wait(), timeout=timeout)

    def complete_with(self, result: DemoResult) -> None:
        """Mark a lazily-created run finished, with the result the live stream computed.
        Idempotent: a run that already carries a result is left as it is, so a second
        stream (e.g. a reconnect) never overwrites the first."""
        if self.result is not None:
            return
        self.result = result
        self.status = "complete"
        self._done.set()


class RunNotFound(KeyError):
    """No run with that id (it never existed, or it has been evicted)."""


class RunNotReady(RuntimeError):
    """The run exists but has not finished, so its results cannot be served yet."""


class RunStore:
    def __init__(self, max_runs: int = MAX_RUNS) -> None:
        self._runs: "OrderedDict[str, Run]" = OrderedDict()
        self._max_runs = max_runs

    # ----- commands -----

    def create(self, scale: str, seed: Optional[int] = None, execute: bool = True) -> Run:
        """Register a run and (by default) start executing it in the background. Returns
        immediately with status 'running'; the caller polls, waits, or streams.

        With execute=False the run is registered but NOT computed here: the live stream
        computes it once, interval by interval, and calls complete_with() when done. This
        is what lets the client render immediately and watch faults appear, instead of
        waiting for a full-scale batch run to finish - and it avoids computing the whole
        pipeline twice (batch and stream) in contention for the GIL."""
        config = config_for_scale(scale, seed)
        run = Run(run_id=uuid.uuid4().hex[:12], scale=scale, config=config,
                  status="running", created_at=time.time())
        self._runs[run.run_id] = run
        self._evict_oldest()
        if execute:
            asyncio.create_task(self._execute(run))
        return run

    async def _execute(self, run: Run) -> None:
        try:
            # run_demo is synchronous and CPU-bound: keep it off the event loop.
            run.result = await run_in_threadpool(run_demo, run.config)
            run.status = "complete"
        except Exception as exc:                      # noqa: BLE001 - surfaced to the client
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {exc}"
        finally:
            run._done.set()

    def _evict_oldest(self) -> None:
        while len(self._runs) > self._max_runs:
            self._runs.popitem(last=False)

    # ----- queries -----

    def get(self, run_id: str) -> Run:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFound(run_id)
        return run

    def get_complete(self, run_id: str) -> Run:
        """The run, guaranteed to carry a result. Raises RunNotReady otherwise, which
        the routers turn into a 409 rather than an empty 200."""
        run = self.get(run_id)
        if run.status == "failed":
            raise RunNotReady(run.error or "the run failed")
        if run.result is None:
            raise RunNotReady("the run has not finished yet")
        return run

    def list(self) -> List[Run]:
        """Newest first."""
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)