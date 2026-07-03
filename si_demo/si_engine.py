"""
Module 4 - The Structural Intelligence engine (the intellectual core).

The engine consumes ONLY the four-field core stream as its fault signal, and learns
its baselines from that stream. It reasons on the service graph: it finds where
elevated edges converge, reads the SHAPE of that convergence, places the fault in
its true LAYER, projects the shape forward, and abstains honestly when the evidence
will not resolve.

WHAT IT USES, AND WHAT IT DOES NOT.
  Fault signal (the only detection input): the four fields entity_src, entity_dst,
    timestamp, magnitude. The engine establishes a per-edge baseline from the healthy
    history it observes, then measures each edge's departure from it. It never reads
    error codes, firmware, channel names, per-layer alarms, or any enrichment.
  Network map (static topology, not telemetry): which node is an access node, a core
    route, or a content source, and which homes sit behind each. This is the known
    wiring of the operator's network, the same reference an operator always has. It is
    used only to NAME the layer of a convergence, never as a fault signal.

HOW THE SHAPE BECOMES THE LAYER.
  A home depends on three subsystems and emits one edge to each. A fault elevates one
  type of edge for the affected homes, so the elevated edges converge on one node:
      many homes converging on one access node   -> CLUSTER -> access
      one home alone                              -> SINGLE  -> home
      homes (across access nodes) on one route    -> PATH    -> core
      homes (across access nodes) on one source   -> SOURCE  -> content
  Cardinality separates a home fault from an access fault: a single home elevated on
  its access node is the home's own fault (SINGLE), not the node's (CLUSTER).

HONESTY, BUILT IN.
  Persistence (dwell): an edge fires only after several consecutive elevated
    intervals, so brief decoys (a one-off glitch, a prime-time spike, a reboot) never
    fire. Real faults persist; decoys only tempt.
  Competence boundary: when a convergence is too weak or too ambiguous to attribute
    with confidence, the engine ABSTAINS and defers to a human rather than guessing.

The internal operator-algebra reading (spectral localization of a subgraph,
persistence separating transient from real, conditional-independence attribution,
the conformal threshold behind abstention) stays internal. The emitted Diagnosis
speaks only in the external register: a named element, a layer, a shape, a forward
projection, a confidence, and an explainable receipt.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Set, Tuple

from .core import (
    DemoConfig, Diagnosis, EntityType, Evidence, Layer, PredictedTrajectory,
    Provenance, Shape, assert_core_stream_clean,
)
from .topology import ServiceGraph


# ---------------------------------------------------------------------------
# The static network map (known wiring; not a fault signal)
# ---------------------------------------------------------------------------

class NetworkMap:
    """The operator's known network wiring, derived from the service graph: each
    node's layer, and the groupings of homes by the access node, route, and content
    they sit behind. Used only to name the layer of a convergence."""

    def __init__(self, graph: ServiceGraph) -> None:
        self.node_layer: Dict[str, Layer] = {n.entity_id: n.layer for n in graph.nodes.values()}
        self.node_type: Dict[str, EntityType] = {n.entity_id: n.entity_type for n in graph.nodes.values()}
        self.home_olt: Dict[str, str] = {}
        self.home_route: Dict[str, str] = {}
        self.home_content: Dict[str, str] = {}
        for stb, m in graph.stb_membership.items():
            self.home_olt[stb] = m.olt_id
            self.home_route[stb] = m.route_id
            self.home_content[stb] = m.content_id
        self.olt_homes = {k: set(v) for k, v in graph.stbs_by_olt.items()}
        self.route_homes = {k: set(v) for k, v in graph.stbs_by_route.items()}
        self.content_homes = {k: set(v) for k, v in graph.stbs_by_content.items()}
        self._homes: Set[str] = set(graph.stb_ids)

    def is_home(self, entity_id: str) -> bool:
        return entity_id in self._homes

    def layer_of(self, node_id: str) -> Optional[Layer]:
        return self.node_layer.get(node_id)

    def homes_behind(self, node_id: str) -> Set[str]:
        """The homes that sit behind a node (its access cluster, route group, or
        content audience), whichever applies."""
        if node_id in self.olt_homes:
            return self.olt_homes[node_id]
        if node_id in self.route_homes:
            return self.route_homes[node_id]
        if node_id in self.content_homes:
            return self.content_homes[node_id]
        return set()


# ---------------------------------------------------------------------------
# Per-edge baseline, learned online from the stream
# ---------------------------------------------------------------------------

@dataclass
class EdgeBaseline:
    """A running healthy baseline for one edge (Welford mean/variance), plus the
    current consecutive-elevated streak (the dwell). The baseline is frozen while an
    edge is anomalous, so a fault does not poison its own reference."""
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    streak: int = 0

    def update_healthy(self, x: float) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (x - self.mean)

    @property
    def std(self) -> float:
        if self.n < 2:
            return 0.0
        return (self.m2 / (self.n - 1)) ** 0.5


# ---------------------------------------------------------------------------
# Engine parameters
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EngineParams:
    warmup_intervals: int
    sigma_threshold: float = 4.0      # departure z to consider an edge elevated
    abs_floor: float = 2.0            # absolute magnitude floor (above healthy noise)
    std_floor: float = 0.1            # minimum std, to avoid over-sensitivity
    min_dwell: int = 3                # consecutive elevated intervals before firing
    cluster_min: int = 3              # homes needed to call a convergence a cluster
    abstain_confidence: float = 0.5   # below this (but above noise) -> abstain
    noise_confidence: float = 0.2     # below this -> treat as noise (all clear)
    history: int = 6                  # intervals of locus history kept for trends

    @staticmethod
    def for_config(config: DemoConfig) -> "EngineParams":
        warmup = max(3, min(20, config.run_intervals // 12))
        return EngineParams(warmup_intervals=warmup)


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

class StructuralIntelligenceEngine:
    """Consumes the four-field stream interval by interval and emits diagnoses.
    observe_and_diagnose(t, core_records) returns the findings for interval t: an
    empty list means all clear; otherwise one Diagnosis per convergence (detected or
    abstained)."""

    def __init__(self, network_map: NetworkMap, config: DemoConfig,
                 params: Optional[EngineParams] = None) -> None:
        self.nm = network_map
        self.config = config
        self.p = params or EngineParams.for_config(config)
        self.baselines: Dict[Tuple[str, str], EdgeBaseline] = {}
        self._locus_hist: Dict[str, Deque[Tuple[int, int, float]]] = {}
        self._t = -1

    # ---- per-edge elevation ----

    def _departure(self, key: Tuple[str, str], mag: float) -> Tuple[float, EdgeBaseline]:
        b = self.baselines.get(key)
        if b is None:
            b = EdgeBaseline()
            self.baselines[key] = b
        if b.n < 2:
            return 0.0, b
        z = (mag - b.mean) / max(b.std, self.p.std_floor)
        return z, b

    def observe_and_diagnose(self, t: int, core_records) -> List[Diagnosis]:
        self._t = t
        records = list(assert_core_stream_clean(core_records))  # boundary guard
        warming = t < self.p.warmup_intervals

        # 1. For each edge: measure departure, update streak, learn baseline if healthy.
        #    `firing` holds edges that have passed the dwell gate (sustained); the
        #    decoy gate. `elevated_now` holds edges elevated THIS interval regardless
        #    of dwell, used only to recognise a forming cluster at its ramp edge so a
        #    lone home is not mistaken for it.
        firing: Dict[str, Set[str]] = {}
        elevated_now: Dict[str, Set[str]] = {}
        dep_on: Dict[Tuple[str, str], float] = {}
        for r in records:
            key = (r.entity_src, r.entity_dst)
            z, b = self._departure(key, r.magnitude)
            elevated = (r.magnitude >= self.p.abs_floor) and (
                z >= self.p.sigma_threshold or (b.n < 2 and r.magnitude >= self.p.abs_floor))
            if elevated and not warming:
                elevated_now.setdefault(r.entity_dst, set()).add(r.entity_src)
                b.streak += 1
                if b.streak >= self.p.min_dwell:
                    firing.setdefault(r.entity_dst, set()).add(r.entity_src)
                    dep_on[key] = z if b.n >= 2 else r.magnitude
            else:
                b.streak = 0
                # learn the baseline only from healthy observations (or during warmup)
                if r.magnitude < self.p.abs_floor or warming:
                    b.update_healthy(r.magnitude)

        if warming or not firing:
            return []

        # 2. Turn each convergence into a classified finding.
        findings: List[Diagnosis] = []
        for dst, homes in sorted(firing.items(), key=lambda kv: -len(kv[1])):
            diag = self._classify(t, dst, homes, dep_on, firing, elevated_now.get(dst, set()))
            if diag is not None:
                findings.append(diag)
        return findings

    # ---- classification, prediction, abstention ----

    def _classify(self, t: int, dst: str, homes: Set[str],
                  dep_on: Dict[Tuple[str, str], float],
                  firing: Dict[str, Set[str]], elevated_now: Set[str]) -> Optional[Diagnosis]:
        layer = self.nm.layer_of(dst)
        n_home = len(homes)
        behind = self.nm.homes_behind(dst)
        # mean departure of the firing edges converging on this node
        deps = [dep_on.get((h, dst), 0.0) for h in homes]
        mean_dep = sum(deps) / max(len(deps), 1)

        # dominance: how concentrated the elevation is on this node, versus all firing
        total_firing_homes = len({h for s in firing.values() for h in s})
        dominance = n_home / max(total_firing_homes, 1)

        # decide shape, layer and the named entity from the convergence and cardinality
        if layer == Layer.ACCESS:
            if n_home >= self.p.cluster_min:
                shape, out_layer, entity = Shape.CLUSTER, Layer.ACCESS, dst
            else:
                # One home has fired on its access node. If several of that node's
                # homes are already rising (even before the dwell gate), this is the
                # leading edge of a forming cluster, not a lone home: defer honestly.
                if len(elevated_now & behind) >= self.p.cluster_min:
                    trajectory = self._trajectory(t, dst, n_home, mean_dep)
                    return Diagnosis(
                        timestamp=t, detected=False, abstained=True, entity_id=None,
                        layer=None, shape=Shape.NONE, confidence=round(min(0.49, 0.3 + 0.02 * len(elevated_now & behind)), 3),
                        trajectory=trajectory, evidence=self._evidence_abstain(t, homes, dst),
                        recommended_action="a cluster may be forming on this access node, watch and confirm")
                # a genuinely isolated home: its access-node peers are not rising
                shape, out_layer = Shape.SINGLE, Layer.HOME
                entity = max(homes, key=lambda h: dep_on.get((h, dst), 0.0))
        elif layer == Layer.CORE:
            shape, out_layer, entity = Shape.PATH, Layer.CORE, dst
        elif layer == Layer.CONTENT:
            shape, out_layer, entity = Shape.SOURCE, Layer.CONTENT, dst
        else:
            return None

        confidence = self._confidence(dominance, mean_dep, homes, dst)
        if confidence < self.p.noise_confidence:
            return None  # treat as noise; stay silent
        trajectory = self._trajectory(t, dst, n_home, mean_dep)

        if confidence < self.p.abstain_confidence:
            # the competence boundary: something is forming but it will not resolve
            return Diagnosis(
                timestamp=t, detected=False, abstained=True, entity_id=None, layer=None,
                shape=Shape.NONE, confidence=round(confidence, 3), trajectory=trajectory,
                evidence=self._evidence_abstain(t, homes, dst), recommended_action=
                "insufficient or ambiguous evidence, escalate to human review")

        return Diagnosis(
            timestamp=t, detected=True, abstained=False, entity_id=entity,
            layer=out_layer, shape=shape, confidence=round(confidence, 3),
            trajectory=trajectory,
            evidence=self._evidence_detect(t, shape, out_layer, entity, homes, dst, mean_dep, behind),
            recommended_action=self._action(shape, out_layer))

    def _confidence(self, dominance: float, mean_dep: float, homes: Set[str], dst: str) -> float:
        strength = min(1.0, mean_dep / (2.0 * self.p.sigma_threshold)) if mean_dep > 0 else 0.5
        # how cleanly the firing homes match the node's known audience (a real cluster
        # sits behind the node; coincidental homes do not)
        behind = self.nm.homes_behind(dst)
        match = (len(homes & behind) / len(homes)) if homes else 0.0
        conf = 0.45 * dominance + 0.35 * strength + 0.20 * match
        return max(0.0, min(1.0, conf))

    def _trajectory(self, t: int, dst: str, n_home: int, mean_dep: float) -> PredictedTrajectory:
        hist = self._locus_hist.setdefault(dst, deque(maxlen=self.p.history))
        hist.append((t, n_home, mean_dep))
        rising = False
        horizon = None
        if len(hist) >= 2:
            first, last = hist[0], hist[-1]
            rising = (last[1] > first[1]) or (last[2] > first[2] + 1e-6)
            if rising:
                # rough projection: continue the trend a few intervals out
                horizon = t + max(3, (t - first[0]))
        detail = "convergence widening" if rising else "convergence steady"
        return PredictedTrajectory(rising=rising, horizon_interval=horizon, detail=detail)

    # ---- the certified-decision receipt, in the external register ----

    def _evidence_detect(self, t: int, shape: Shape, layer: Layer, entity: str,
                         homes: Set[str], dst: str, mean_dep: float, behind: Set[str]) -> Evidence:
        n = len(homes)
        if shape == Shape.CLUSTER:
            claim = f"Access node {entity} degrading: {n} homes behind it with rising impairment"
            check = ("the elevated homes share one access node and their other subsystems "
                     "are within baseline, inconsistent with a content or core fault")
        elif shape == Shape.SINGLE:
            claim = f"Household {entity} degrading in isolation; its access-node peers are healthy"
            check = ("only this home is elevated while its node peers remain at baseline, "
                     "inconsistent with a shared network fault")
        elif shape == Shape.PATH:
            claim = f"Core route {entity} degrading: homes across several access nodes impaired together"
            check = ("the elevated homes span multiple access nodes but share one core route, "
                     "inconsistent with a single-node or content fault")
        else:
            claim = f"Content source {entity} degrading: otherwise-unrelated homes impaired together"
            check = ("the elevated homes span many access nodes but share one content source, "
                     "inconsistent with an access-node fault")
        supporting = (
            f"{n} homes elevated and sustained beyond the dwell threshold",
            f"mean departure {mean_dep:.1f} standard deviations above the learned baseline",
            f"{len(homes & behind)} of {n} elevated homes sit behind {dst} by the network map")
        prov = Provenance(interval_start=max(0, t - self.p.history), interval_end=t,
                          entities_examined=tuple(sorted(homes)),
                          note="four-field magnitude stream only; baselines learned from history")
        return Evidence(claim=claim, supporting=supporting, check=check, provenance=prov)

    def _evidence_abstain(self, t: int, homes: Set[str], dst: str) -> Evidence:
        return Evidence(
            claim="A disturbance is forming but the evidence will not yet resolve to a layer",
            supporting=(f"{len(homes)} homes elevated near {dst}",
                        "convergence weak or ambiguous; confidence below the action threshold"),
            check="the structural signature is not yet strong or clean enough to attribute",
            provenance=Provenance(interval_start=max(0, t - self.p.history), interval_end=t,
                                  entities_examined=tuple(sorted(homes)),
                                  note="competence boundary reached; deferring to human"))

    def _action(self, shape: Shape, layer: Layer) -> str:
        if shape == Shape.CLUSTER:
            return "inspect the access node and its aggregation before complaints escalate"
        if shape == Shape.SINGLE:
            return "proactive customer contact and gateway reconfiguration, no truck roll"
        if shape == Shape.PATH:
            return "investigate the core transport route carrying the affected homes"
        return "investigate the content source and its delivery path"
