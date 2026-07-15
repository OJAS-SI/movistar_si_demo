"""
Interval-by-interval replay, for the live stream.

run_demo() executes the whole pipeline and hands back the finished picture. That is
the right shape for the console and the scorecard, but it cannot show the one thing
the demo is really about: the engine watching a shape form, interval by interval,
before the fault surfaces.

So this rebuilds the same pipeline and steps it. The rebuild is free of risk because
the run is deterministic from the seed: replaying a config produces exactly the
diagnoses the completed run produced. Nothing here is a second, divergent code path -
it is the same components, driven one interval at a time.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterator, List, Optional, Tuple

from si_core.contracts import DemoConfig, Diagnosis
from si_core.fault_injection import FaultInjector
from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
from si_core.topology import ServiceGraph, build_service_graph

# One replayed interval: the interval index, its core magnitudes, whatever the engine
# concluded, and any ground-truth fault that began here.
Frame = Tuple[int, List[float], List[Diagnosis], List[str]]

# What replay() hands back when the stream is exhausted: the pieces needed to assemble
# the finished run WITHOUT recomputing it - the graph, the injector (which carries the
# schedule and ground truth), and every interval's diagnoses as they were collected.
Collected = Tuple[ServiceGraph, FaultInjector, Dict[int, List[Diagnosis]]]


class Done:
    """Signals the end of the stream and carries the collected pipeline as its value.
    A plain StopIteration cannot cross the worker-thread boundary into asyncio (it
    surfaces as an opaque RuntimeError), so the end is returned as a value instead."""

    def __init__(self, collected: Collected) -> None:
        self.collected = collected


def replay(config: DemoConfig) -> "Iterator[Frame]":
    """Step the pipeline one interval at a time, yielding what the engine saw and said,
    and RETURN the collected pipeline (graph, injector, per-interval diagnoses) when done.

    The engine is fed only injector.interval(t).core - the four-field stream - exactly
    as in the batch run. Enrichment is never handed to it here either. Because every
    diagnosis is retained, the caller can assemble the exact same console and scorecard
    the batch run would produce, from this single interval-by-interval computation.
    """
    graph = build_service_graph(config)
    injector = FaultInjector(graph, config)
    engine = StructuralIntelligenceEngine(NetworkMap(graph), config)

    onsets: Dict[int, List[str]] = defaultdict(list)
    for spec in injector.schedule:
        onsets[spec.onset].append(spec.fault_id)

    per_interval: Dict[int, List[Diagnosis]] = {}
    for t in range(config.run_intervals):
        telemetry = injector.interval(t)
        diagnoses = engine.observe_and_diagnose(t, telemetry.core)
        per_interval[t] = diagnoses
        magnitudes = [rec.magnitude for rec in telemetry.core]
        yield t, magnitudes, diagnoses, list(onsets.get(t, ()))

    return (graph, injector, per_interval)


def next_frame(frames: "Iterator[Frame]"):
    """Pull one frame, or a Done (carrying the collected pipeline) when exhausted.

    The caller advances this generator inside a worker thread (each interval is real CPU
    work, and the event loop must stay free). A StopIteration escaping a thread boundary
    into asyncio surfaces as an opaque RuntimeError, so the end of the stream - and the
    generator's return value - is signalled as a Done value instead.
    """
    try:
        return next(frames)
    except StopIteration as stop:
        return Done(stop.value)