"""
Runs, and everything one run produced.

A run is created, executed in the background, and then queried. Every read endpoint
below serves from the single DemoResult that execution produced, so the console, the
scorecard and the topology can never disagree with one another.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Query, status
from fastapi.responses import HTMLResponse

from ..dependencies import StoreDep
from ..serializers import config_out, console_out, diagnosis_out, scorecard_out, topology_out
from ..services.run_store import Run
from ..schemas import (
    ConsoleOut, DiagnosisOut, RunOut, RunRequest, ScaleName, ScorecardOut, TopologyOut,
)

router = APIRouter(prefix="/runs", tags=["runs"])


def _run_out(run: Run) -> RunOut:
    return RunOut(
        run_id=run.run_id, scale=run.scale, seed=run.seed, status=run.status,
        created_at=run.created_at, config=config_out(run.config),
        runtime_seconds=run.runtime_seconds, passed=run.passed,
        summary=run.summary, error=run.error,
    )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED,
             summary="Start a run")
async def create_run(
    body: RunRequest,
    store: StoreDep,
    wait_seconds: float = Query(
        default=0.0, ge=0.0, le=300.0,
        description="Block up to this long for the run to finish before responding. "
                    "A tiny run takes well under a second, so the client can simply "
                    "ask for the answer; a full run is better polled or streamed."),
    execute: bool = Query(
        default=True,
        description="Compute the run here, in the background. Set false to register it "
                    "without computing: the live stream then computes it once and stores "
                    "the result, so the client can render immediately and watch faults "
                    "appear rather than wait for a full-scale run to finish."),
) -> RunOut:
    """Execute the pipeline at the given scale and seed.

    The run is deterministic: the same scale and seed always reproduce the same graph,
    the same faults, the same verdicts, and the same console.
    """
    run = store.create(body.scale, body.seed, execute=execute)
    if wait_seconds > 0:
        try:
            await run.wait(timeout=wait_seconds)
        except asyncio.TimeoutError:
            pass          # still running; the client gets status="running" and can poll
    return _run_out(run)


@router.get("", response_model=List[RunOut], summary="List runs, newest first")
def list_runs(store: StoreDep) -> List[RunOut]:
    return [_run_out(r) for r in store.list()]


@router.get("/{run_id}", response_model=RunOut, summary="One run and its status")
def get_run(run_id: str, store: StoreDep) -> RunOut:
    return _run_out(store.get(run_id))


# ---------------------------------------------------------------------------
# What the run produced
# ---------------------------------------------------------------------------

@router.get("/{run_id}/console", response_model=ConsoleOut,
            summary="The operator console: the four-beat narrative, the honest instruments, the scorecard")
def get_console(run_id: str, store: StoreDep) -> ConsoleOut:
    """The whole story of the run in one payload. This is what the React console renders."""
    run = store.get_complete(run_id)
    return console_out(run.result.console_model, run.result.passed())


@router.get("/{run_id}/scorecard", response_model=ScorecardOut,
            summary="Measured scores against ground truth")
def get_scorecard(run_id: str, store: StoreDep) -> ScorecardOut:
    run = store.get_complete(run_id)
    return scorecard_out(run.result.score_report, run.result.passed())


@router.get("/{run_id}/diagnoses", response_model=List[DiagnosisOut],
            summary="The verdicts the run settled on")
def get_diagnoses(run_id: str, store: StoreDep) -> List[DiagnosisOut]:
    """One diagnosis per use case (the element the engine settled on, taken while the
    fault was still forming), plus the abstention if the engine declined anywhere.

    For every diagnosis at every interval, stream the run instead.
    """
    run = store.get_complete(run_id)
    model = run.result.console_model
    out = [diagnosis_out(p.report.diagnosis) for p in model.fault_panels
           if p.report.diagnosis is not None]
    abstention = model.honest.abstention
    if abstention is not None and abstention.diagnosis is not None:
        out.append(diagnosis_out(abstention.diagnosis))
    return out


@router.get("/{run_id}/topology", response_model=TopologyOut,
            summary="The static service graph this run was built on")
def get_topology(
    run_id: str,
    store: StoreDep,
    entity_type: Optional[str] = Query(
        default=None, description="Filter to one type: stb, ont, olt, agg, bng, core, "
                                  "cdn_edge, content."),
    region: Optional[str] = Query(default=None, description="Filter to one region name."),
    limit: int = Query(default=500, ge=1, le=20000,
                       description="Cap on returned nodes. A full run has thousands."),
) -> TopologyOut:
    """The nodes and their hierarchy. The counts always describe the whole graph, even
    when the node list is capped - `truncated` says whether it was."""
    run = store.get_complete(run_id)
    graph = run.result.graph

    nodes = list(graph.nodes.values())
    if entity_type:
        nodes = [n for n in nodes if n.entity_type.value == entity_type]
    if region:
        nodes = [n for n in nodes if n.region == region]

    truncated = len(nodes) > limit
    return topology_out(graph, nodes[:limit], truncated)


@router.get("/{run_id}/console.html", response_class=HTMLResponse,
            summary="The self-contained HTML console (the original artifact)")
def get_console_html(run_id: str, store: StoreDep) -> HTMLResponse:
    """The same single-file console the CLI writes to disk, served over HTTP. Kept so
    the pre-existing artifact stays reachable and nothing regresses."""
    run = store.get_complete(run_id)
    return HTMLResponse(run.result.html_console)