"""
The seam between the domain and the wire.

This is the ONLY module in the codebase that imports both si_core (frozen, pure
standard library) and si_api.schemas (Pydantic). Everything here maps one way:
domain dataclass -> wire schema. Nothing maps back, because the API never asks the
engine to accept a foreign shape; a run is described by a config, and a config is
built by the domain itself.

Keeping the mapping in one file is what makes the layering enforceable: if si_core
ever grows a Pydantic import, or a router ever reaches into a domain dataclass, it is
visible here as a diff, not buried across the codebase.
"""

from __future__ import annotations

from typing import List, Optional

from si_core.console import ConsoleModel, FaultPanel, HonestPanel
from si_core.contracts import DemoConfig, Diagnosis, Evidence, PredictedTrajectory, Provenance, Score
from si_core.diagnosis import DiagnosisReport, ReceiptCard
from si_core.scoring import ScoreReport
from si_core.topology import Node, ServiceGraph

from . import schemas as s


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def scale_of(config: DemoConfig) -> str:
    """Which named scale a config represents. Mirrors the rule the CLI summary uses."""
    return "full" if len(config.regions) >= 6 and config.n_stb_target > 200 else "tiny"


def config_out(config: DemoConfig) -> s.ConfigOut:
    return s.ConfigOut(
        seed=config.seed,
        scale=scale_of(config),
        n_homes_target=config.n_stb_target,
        interval_seconds=config.interval_seconds,
        run_intervals=config.run_intervals,
        regions=[
            s.RegionOut(name=r.name, province_code=r.province_code,
                        central_office_names=list(r.central_office_names), weight=r.weight)
            for r in config.regions
        ],
    )


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

def node_out(node: Node) -> s.NodeOut:
    return s.NodeOut(entity_id=node.entity_id, entity_type=node.entity_type.value,
                     layer=node.layer.value, parent_id=node.parent_id, region=node.region)


def topology_out(graph: ServiceGraph, nodes: List[Node], truncated: bool) -> s.TopologyOut:
    return s.TopologyOut(
        n_nodes=len(graph.nodes),
        n_homes=len(graph.stb_ids),
        n_access_nodes=len(graph.olt_ids),
        counts_by_type=graph.summary(),
        regions=[r.name for r in graph.config.regions],
        nodes=[node_out(n) for n in nodes],
        truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Diagnosis, evidence, receipt
# ---------------------------------------------------------------------------

def provenance_out(p: Provenance) -> s.ProvenanceOut:
    return s.ProvenanceOut(interval_start=p.interval_start, interval_end=p.interval_end,
                           entities_examined=list(p.entities_examined), note=p.note)


def evidence_out(e: Evidence) -> s.EvidenceOut:
    return s.EvidenceOut(claim=e.claim, supporting=list(e.supporting), check=e.check,
                         provenance=provenance_out(e.provenance))


def trajectory_out(t: PredictedTrajectory) -> s.TrajectoryOut:
    return s.TrajectoryOut(rising=t.rising, horizon_interval=t.horizon_interval, detail=t.detail)


def diagnosis_out(d: Diagnosis) -> s.DiagnosisOut:
    return s.DiagnosisOut(
        timestamp=d.timestamp, detected=d.detected, abstained=d.abstained,
        entity_id=d.entity_id, layer=d.layer.value if d.layer else None,
        shape=d.shape.value, confidence=d.confidence,
        recommended_action=d.recommended_action,
        trajectory=trajectory_out(d.trajectory) if d.trajectory else None,
        evidence=evidence_out(d.evidence) if d.evidence else None,
    )


def receipt_out(r: ReceiptCard) -> s.ReceiptOut:
    return s.ReceiptOut(claim=r.claim, evidence_lines=list(r.evidence_lines), check=r.check,
                        provenance=r.provenance, confidence=r.confidence)


def report_out(rep: DiagnosisReport) -> s.ReportOut:
    return s.ReportOut(
        timestamp=rep.timestamp, kind=rep.kind, headline=rep.headline,
        health_band=rep.health_band,
        receipt=receipt_out(rep.receipt) if rep.receipt else None,
        diagnosis=diagnosis_out(rep.diagnosis) if rep.diagnosis else None,
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_out(score: Score, interval_seconds: int) -> s.ScoreOut:
    lead = score.mean_lead_time_intervals
    return s.ScoreOut(
        use_case=score.use_case.value if score.use_case else None,
        n_faults=score.n_faults, n_detected=score.n_detected,
        mean_lead_time_intervals=lead,
        mean_lead_time_minutes=(lead * interval_seconds / 60) if lead is not None else None,
        localization_accuracy=score.localization_accuracy,
        layer_attribution_accuracy=score.layer_attribution_accuracy,
        box_swap_discrimination=score.box_swap_discrimination,
        false_positive_rate=score.false_positive_rate,
        action_correctness=score.action_correctness,
        note=score.note,
    )


def scorecard_out(report: ScoreReport, passed: bool) -> s.ScorecardOut:
    return s.ScorecardOut(
        per_use_case=[score_out(sc, report.interval_seconds) for sc in report.per_use_case],
        false_positive_rate=report.false_positive_rate,
        n_non_fault_intervals=report.n_non_fault_intervals,
        n_spurious_intervals=report.n_spurious_intervals,
        n_decoys=report.n_decoys, n_decoys_fired=report.n_decoys_fired,
        interval_seconds=report.interval_seconds, notes=list(report.notes),
        passed=passed, text=report.render(),
    )


# ---------------------------------------------------------------------------
# The console
# ---------------------------------------------------------------------------

def fault_panel_out(panel: FaultPanel, interval_seconds: int) -> s.FaultPanelOut:
    d = panel.report.diagnosis
    return s.FaultPanelOut(
        use_case=panel.use_case.value, title=panel.title,
        beats=[s.BeatOut(name=b.name, text=b.text) for b in panel.beats],
        entity=panel.entity, region=panel.region,
        layer=d.layer.value if d and d.layer else None,
        shape=panel.shape.value, affected=list(panel.affected),
        report=report_out(panel.report),
        score=score_out(panel.score, interval_seconds),
    )


def honest_panel_out(honest: HonestPanel) -> s.HonestPanelOut:
    return s.HonestPanelOut(
        abstention=report_out(honest.abstention) if honest.abstention else None,
        n_decoys=honest.n_decoys, n_decoys_fired=honest.n_decoys_fired,
        false_positive_rate=honest.false_positive_rate,
        n_non_fault_intervals=honest.n_non_fault_intervals,
        n_spurious_intervals=honest.n_spurious_intervals,
    )


def console_out(model: ConsoleModel, passed: bool) -> s.ConsoleOut:
    interval_seconds = model.score_report.interval_seconds
    return s.ConsoleOut(
        title=model.title, subtitle=model.subtitle, config_summary=model.config_summary,
        fault_panels=[fault_panel_out(p, interval_seconds) for p in model.fault_panels],
        honest=honest_panel_out(model.honest),
        scorecard=scorecard_out(model.score_report, passed),
    )


# ---------------------------------------------------------------------------
# Stream frames
# ---------------------------------------------------------------------------

def frame_out(timestamp: int, total_intervals: int, magnitudes: List[float],
              diagnoses: List[Diagnosis], fault_onsets: List[str]) -> s.StreamFrameOut:
    n = len(magnitudes)
    return s.StreamFrameOut(
        timestamp=timestamp, total_intervals=total_intervals, n_core_records=n,
        mean_magnitude=(sum(magnitudes) / n) if n else 0.0,
        max_magnitude=max(magnitudes) if magnitudes else 0.0,
        diagnoses=[diagnosis_out(d) for d in diagnoses],
        fault_onsets=fault_onsets,
    )