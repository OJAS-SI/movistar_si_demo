"""
The live stream: the run, replayed one interval at a time over a WebSocket.

This is the endpoint that shows the claim rather than asserting it. The client watches
magnitudes drift, sees the interval a fault actually began (a ground-truth onset), and
then sees the interval the engine named it - the gap between those two is the lead
time the scorecard reports.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

import time
from typing import List

from si_core.orchestrator import assemble_result

from ..dependencies import CatalogueWsDep, StoreWsDep
from ..schemas import StreamEndOut, StreamErrorOut
from ..serializers import cached_frame_out
from ..services.replay import Done, next_frame, replay
from ..services.run_store import CachedFrame, Run, RunNotFound

router = APIRouter(tags=["stream"])

# WebSocket close codes.
# How long the stream will wait for a run that is already being computed elsewhere,
# rather than recomputing it. A full run takes ~84s from cold; beyond this the stream
# gives up waiting and computes, which is slower but never hangs.
WARM_WAIT_SECONDS = 150.0

CLOSE_NOT_FOUND = 4404
CLOSE_INTERNAL = 4500


@router.websocket("/runs/{run_id}/stream")
async def stream_run(
    websocket: WebSocket,
    run_id: str,
    store: StoreWsDep,
    cat: CatalogueWsDep,
    interval_ms: int = Query(
        default=60, ge=0, le=5000,
        description="Delay between frames, in milliseconds. 0 replays as fast as the "
                    "engine can compute."),
) -> None:
    """Replay the run's intervals in order.

    Frames are `{type: "frame", ...}` and the stream closes with `{type: "end"}`. The
    replay is computed from the run's config, which is deterministic, so it reproduces
    exactly the diagnoses the completed run holds.
    """
    await websocket.accept()

    try:
        run = store.get(run_id)
    except RunNotFound:
        await websocket.send_json(StreamErrorOut(detail=f"No run {run_id!r}.").model_dump())
        await websocket.close(code=CLOSE_NOT_FOUND)
        return

    config = run.config
    delay = interval_ms / 1000.0
    started = time.time()

    # A run that has already been streamed once carries every interval it produced. That
    # is the case a scale toggle hits, and replaying from it costs nothing - where
    # recomputing the full network costs ~84s. The frames are domain values, so they are
    # still serialised into this socket's language.
    # Someone is already computing this run - prewarm at startup, or an eager create.
    # Wait for it instead of stepping the same 576 intervals a second time.
    if run.frames is None and run.executing and run.status == "running":
        try:
            await run.wait(timeout=WARM_WAIT_SECONDS)
        except asyncio.TimeoutError:
            pass                                  # fall through and compute it here

    if run.frames is not None:
        try:
            for cached in run.frames:
                await websocket.send_json(
                    cached_frame_out(cached, config.run_intervals, cat).model_dump())
                if delay:
                    await asyncio.sleep(delay)
            await websocket.send_json(
                StreamEndOut(total_intervals=config.run_intervals).model_dump())
            await websocket.close()
        except WebSocketDisconnect:
            pass
        return

    collected_frames: List[CachedFrame] = []
    frames = replay(config)

    try:
        while True:
            # Each interval is real CPU work (telemetry, injection, detection), so it
            # runs in a worker thread and the event loop stays free to push frames.
            frame = await run_in_threadpool(next_frame, frames)
            if isinstance(frame, Done):
                # The stream is exhausted; `frame` carries the collected pipeline. Assemble
                # the finished run from it once - no recomputation - and hand it to the
                # store, so the REST console, scorecard and topology become available for a
                # run that was created lazily (execute=false).
                await _finalize(run, frame, started)
                # Only now, complete: a half-collected list would make the next stream
                # replay a truncated run and look like the engine stopped early.
                run.frames = collected_frames
                break
            timestamp, magnitudes, diagnoses, onsets = frame
            n = len(magnitudes)
            cached = CachedFrame(
                timestamp=timestamp, n_core_records=n,
                mean_magnitude=(sum(magnitudes) / n) if n else 0.0,
                max_magnitude=max(magnitudes) if magnitudes else 0.0,
                diagnoses=tuple(diagnoses), fault_onsets=tuple(onsets))
            collected_frames.append(cached)
            await websocket.send_json(
                cached_frame_out(cached, config.run_intervals, cat).model_dump())
            if delay:
                await asyncio.sleep(delay)

        await websocket.send_json(StreamEndOut(total_intervals=config.run_intervals).model_dump())
        await websocket.close()

    except WebSocketDisconnect:
        pass                                  # the client walked away; nothing to clean up
    except Exception as exc:                  # noqa: BLE001 - report, then close cleanly
        try:
            await websocket.send_json(
                StreamErrorOut(detail=f"{type(exc).__name__}: {exc}").model_dump())
            await websocket.close(code=CLOSE_INTERNAL)
        except (WebSocketDisconnect, RuntimeError):
            pass


async def _finalize(run: Run, done: Done, started: float) -> None:
    """Assemble the finished run from the stream's collected pipeline and store it, once.
    Assembly (scoring, console, HTML) is light next to the interval work already done, but
    it is still pure CPU, so it runs off the event loop."""
    if run.result is not None:
        return
    graph, injector, per_interval = done.collected
    result = await run_in_threadpool(
        assemble_result, graph, injector, per_interval, run.config, time.time() - started)
    run.complete_with(result)