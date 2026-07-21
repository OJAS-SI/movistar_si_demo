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
from typing import Dict, List, Optional, Tuple

from starlette.concurrency import run_in_threadpool

from si_core.contracts import DemoConfig, Diagnosis
from si_core.orchestrator import DemoResult, assemble_result, config_for_scale


@dataclass(frozen=True, slots=True)
class CachedFrame:
    """One replayed interval, kept so a run only ever has to be stepped once.

    The per-record magnitudes are NOT kept - only the two aggregates the wire carries -
    because holding 576 x 2400 floats per full run would cost tens of megabytes to
    re-send two numbers. The diagnoses are kept as domain objects rather than as
    rendered JSON, so a cached frame still serialises into whichever language the
    socket asked for."""
    timestamp: int
    n_core_records: int
    mean_magnitude: float
    max_magnitude: float
    diagnoses: Tuple[Diagnosis, ...]
    fault_onsets: Tuple[str, ...]

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
    # Every interval this run replayed, filled in by the first stream. A second stream
    # of the same run - which is what a toggle back to this scale is - replays from
    # here instead of recomputing 576 intervals.
    frames: Optional[List[CachedFrame]] = None
    # True when something is already computing this run (prewarm, or an eager create).
    # The stream waits for that rather than starting a second, identical computation.
    executing: bool = False
    _done: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    @property
    def key(self) -> Tuple[str, int]:
        """What makes two runs the same run. A run is deterministic from its scale and
        seed, so this is identity, not a cache key with a staleness problem."""
        return (self.scale, self.config.seed)

    @property
    def warm(self) -> bool:
        """Ready to be shown instantly: computed, and its stream already cached."""
        return self.result is not None and self.frames is not None

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


def _replay_and_assemble(config: DemoConfig) -> Tuple[List[CachedFrame], DemoResult]:
    """Step a run interval by interval, keeping each frame, then assemble the result.

    Synchronous and CPU-bound on purpose: the caller puts it on a worker thread. This is
    the same code path the live stream drives, so a prewarmed run and a streamed one are
    the same run - not two implementations that have to agree."""
    from .replay import Done, next_frame, replay          # local: avoids an import cycle

    started = time.time()
    frames: List[CachedFrame] = []
    stepper = replay(config)
    while True:
        frame = next_frame(stepper)
        if isinstance(frame, Done):
            graph, injector, per_interval = frame.collected
            result = assemble_result(graph, injector, per_interval, config,
                                     time.time() - started)
            return frames, result
        timestamp, magnitudes, diagnoses, onsets = frame
        n = len(magnitudes)
        frames.append(CachedFrame(
            timestamp=timestamp, n_core_records=n,
            mean_magnitude=(sum(magnitudes) / n) if n else 0.0,
            max_magnitude=max(magnitudes) if magnitudes else 0.0,
            diagnoses=tuple(diagnoses), fault_onsets=tuple(onsets)))


class RunNotFound(KeyError):
    """No run with that id (it never existed, or it has been evicted)."""


class RunNotReady(RuntimeError):
    """The run exists but has not finished, so its results cannot be served yet."""


class RunStore:
    def __init__(self, max_runs: int = MAX_RUNS) -> None:
        self._runs: "OrderedDict[str, Run]" = OrderedDict()
        self._by_key: Dict[Tuple[str, int], str] = {}
        self._max_runs = max_runs

    def find(self, scale: str, seed: Optional[int] = None) -> Optional[Run]:
        """The run already held for this scale and seed, if any."""
        config = config_for_scale(scale, seed)
        run_id = self._by_key.get((scale, config.seed))
        return self._runs.get(run_id) if run_id else None

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

        # A run is deterministic from (scale, seed), so an existing one for the same pair
        # IS this run - not a cache of it. Returning it is what makes toggling between
        # scales instant instead of paying 84s for the full network again. A previous
        # attempt that failed is not reused; it is replaced.
        existing = self.find(scale, seed)
        if existing is not None and existing.status != "failed":
            self._runs.move_to_end(existing.run_id)
            return existing

        run = Run(run_id=uuid.uuid4().hex[:12], scale=scale, config=config,
                  status="running", created_at=time.time())
        self._runs[run.run_id] = run
        self._by_key[run.key] = run.run_id
        self._evict_oldest()
        if execute:
            run.executing = True
            asyncio.create_task(self._execute(run))
        return run

    async def prewarm(self, scales: Tuple[str, ...] = ("tiny", "full")) -> None:
        """Compute the demo's runs before anyone asks for one.

        The full network takes ~84s. Paid on startup that is invisible; paid when the
        presenter reaches for the toggle it is the whole demo stalling. Runs execute one
        at a time and in a worker thread, so the server answers requests throughout and
        the two runs do not contend for the GIL with each other."""
        for scale in scales:
            run = self.create(scale, execute=True)
            try:
                await run.wait()
            except Exception:                  # noqa: BLE001 - a failed prewarm is not fatal
                continue

    async def _execute(self, run: Run) -> None:
        """Compute the run by REPLAYING it, then assembling the result from what the
        replay collected.

        The obvious implementation calls run_demo(), but that produces only the finished
        picture - and the client also needs every interval for the transport ribbon, which
        would then be computed a second time by the stream. Stepping the replay once
        yields both: the frames, and (via assemble_result) exactly the DemoResult run_demo
        would have produced, from the same collected diagnoses."""
        try:
            frames, result = await run_in_threadpool(_replay_and_assemble, run.config)
            run.result = result
            run.frames = frames
            run.status = "complete"
        except Exception as exc:                      # noqa: BLE001 - surfaced to the client
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {exc}"
        finally:
            run._done.set()

    def _evict_oldest(self) -> None:
        while len(self._runs) > self._max_runs:
            _, evicted = self._runs.popitem(last=False)
            # keep the key index in step, or find() hands back a run that is gone
            if self._by_key.get(evicted.key) == evicted.run_id:
                del self._by_key[evicted.key]

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