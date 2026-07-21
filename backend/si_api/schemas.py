"""
The API contract: every shape that crosses the wire.

This module is the single, readable statement of what the frontend may rely on. It
imports nothing from si_core - these are transport types, not domain types, and the
one-way mapping between them lives in serializers.py. Keeping them apart is what lets
the domain stay pure standard library while the API speaks Pydantic and OpenAPI.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ScaleName = Literal["tiny", "full"]
RunStatus = Literal["running", "complete", "failed"]


class Schema(BaseModel):
    """Base for every wire type: reject unknown fields, so a typo in a payload is a
    400 rather than a silently ignored key."""
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Health and configuration
# ---------------------------------------------------------------------------

class HealthOut(Schema):
    status: Literal["ok"]
    api_version: str
    core_version: str
    frozen_contract_version: str = Field(
        description="The version of the frozen four-field contract the core is built against.")


class RegionOut(Schema):
    name: str
    province_code: str
    central_office_names: List[str]
    weight: float


class ConfigOut(Schema):
    """The configuration a run was executed with. A run is fully determined by this."""
    seed: int
    scale: ScaleName
    n_homes_target: int
    interval_seconds: int
    run_intervals: int
    regions: List[RegionOut]


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class RunRequest(Schema):
    """Start a run. Same scale and seed always reproduce the same run, byte for byte."""
    scale: ScaleName = "tiny"
    seed: Optional[int] = Field(
        default=None, ge=0,
        description="Override the seed. Omit for the canonical seed for this scale.")


class RunOut(Schema):
    run_id: str
    scale: ScaleName
    seed: int
    status: RunStatus
    created_at: float
    config: ConfigOut
    runtime_seconds: Optional[float] = None
    # True when this run is computed AND its replay is cached, i.e. selecting this scale
    # will render immediately rather than computing.
    warm: bool = False
    passed: Optional[bool] = Field(
        default=None,
        description="The internal self-test: all faults detected and attributed, box "
                    "swap avoided, no false positives. Null until the run completes.")
    summary: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

class NodeOut(Schema):
    entity_id: str
    entity_type: str
    layer: str
    parent_id: Optional[str]
    region: str


class TopologyOut(Schema):
    n_nodes: int
    n_homes: int
    n_access_nodes: int
    counts_by_type: Dict[str, int]
    regions: List[str]
    nodes: List[NodeOut]
    truncated: bool = Field(
        description="True when `nodes` was capped by the limit; counts above are still "
                    "for the whole graph.")


# ---------------------------------------------------------------------------
# Diagnosis, evidence, receipt
# ---------------------------------------------------------------------------

class ProvenanceOut(Schema):
    interval_start: int
    interval_end: int
    entities_examined: List[str]
    note: str


class EvidenceOut(Schema):
    claim: str
    supporting: List[str]
    check: str
    provenance: ProvenanceOut


class TrajectoryOut(Schema):
    rising: bool
    horizon_interval: Optional[int]
    detail: str


class DiagnosisOut(Schema):
    """One verdict from the Structural Intelligence engine, in the external register."""
    timestamp: int
    detected: bool
    abstained: bool
    entity_id: Optional[str]
    layer: Optional[str]
    shape: str
    confidence: float
    recommended_action: Optional[str]
    # The recommendation as a stable code. `recommended_action` is prose and changes
    # with the requested language; anything programmatic should read this instead.
    action_code: Optional[str] = None
    trajectory: Optional[TrajectoryOut]
    evidence: Optional[EvidenceOut]


class ReceiptOut(Schema):
    """The certified-decision receipt: claim, evidence, an independent check, provenance."""
    claim: str
    evidence_lines: List[str]
    check: str
    provenance: str
    confidence: float


class ReportOut(Schema):
    timestamp: int
    kind: str
    headline: str
    health_band: str
    # Title forms of the two above, for a heading and a badge. Same facts, fewer words;
    # they fall back to the full text when a catalogue has no short wording.
    headline_short: str = ""
    health_band_short: str = ""
    receipt: Optional[ReceiptOut]
    diagnosis: Optional[DiagnosisOut]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class ScoreOut(Schema):
    """Measured values only. No success threshold is fixed anywhere in this contract."""
    use_case: Optional[str]
    n_faults: int
    n_detected: int
    mean_lead_time_intervals: Optional[float]
    mean_lead_time_minutes: Optional[float]
    localization_accuracy: Optional[float]
    layer_attribution_accuracy: Optional[float]
    box_swap_discrimination: Optional[float]
    false_positive_rate: Optional[float]
    action_correctness: Optional[float]
    note: str


class ScorecardOut(Schema):
    per_use_case: List[ScoreOut]
    false_positive_rate: float
    n_non_fault_intervals: int
    n_spurious_intervals: int
    n_decoys: int
    n_decoys_fired: int
    interval_seconds: int
    notes: List[str]
    passed: bool
    text: str = Field(description="The rendered plain-text scorecard, for parity with the CLI.")


# ---------------------------------------------------------------------------
# The operator console (the four-beat narrative)
# ---------------------------------------------------------------------------

class BeatOut(Schema):
    name: str
    text: str


class FaultPanelOut(Schema):
    use_case: str
    title: str
    # Ground-truth onset for THIS fault. `use_case` does not identify a panel - a full
    # run has 13 uc1 panels - so the client must not join onsets by use case.
    onset_interval: Optional[int] = None
    beats: List[BeatOut]
    entity: str
    region: str
    layer: Optional[str]
    shape: str
    affected: List[str]
    report: ReportOut
    score: ScoreOut


class HonestPanelOut(Schema):
    """The instruments that keep the demo honest: an abstention, the decoys that did
    not fire, and the measured false-positive rate."""
    abstention: Optional[ReportOut]
    n_decoys: int
    n_decoys_fired: int
    false_positive_rate: float
    n_non_fault_intervals: int
    n_spurious_intervals: int


class ConsoleOut(Schema):
    title: str
    subtitle: str
    config_summary: str
    fault_panels: List[FaultPanelOut]
    honest: HonestPanelOut
    scorecard: ScorecardOut


# ---------------------------------------------------------------------------
# The live stream (WebSocket)
# ---------------------------------------------------------------------------

class StreamFrameOut(Schema):
    """One interval, replayed. This is what the four-field stream looks like from the
    outside: a magnitude summary and whatever the engine concluded this interval."""
    type: Literal["frame"] = "frame"
    timestamp: int
    total_intervals: int
    n_core_records: int
    mean_magnitude: float
    max_magnitude: float
    diagnoses: List[DiagnosisOut]
    fault_onsets: List[str] = Field(
        default_factory=list,
        description="Ground-truth fault ids whose onset is this interval. Shown so the "
                    "UI can mark when a fault began, versus when the engine caught it.")


class StreamEndOut(Schema):
    type: Literal["end"] = "end"
    total_intervals: int


class StreamErrorOut(Schema):
    type: Literal["error"] = "error"
    detail: str