"""
Module 3 - Fault-injection engine and ground-truth recorder.

This is the heart of the demo's scientific validity: every fault it injects, it
records, so every diagnosis downstream can be scored against a known answer. The
demo therefore has GROUND TRUTH BY CONSTRUCTION.

It wraps Module 2's healthy telemetry and perturbs it. Each use case is mapped onto
exactly the subsystem edge whose shape it should produce, so the four shapes stay
cleanly separable:

    UC1  gradual OLT degradation   -> raise the ACCESS edge of every home behind one
         (network node)               OLT. Shape: a CLUSTER on that OLT -> access layer.

    UC2  isolated home decline     -> raise the ACCESS edge of ONE home; its OLT peers
         (individual)                 stay flat. Shape: a SINGLE home -> home layer.
                                      A tipping point is recorded for lead-time scoring.

    UC3  invisible fault           -> raise the ACCESS edge of a small SEGMENT of homes
         (survives box swap)          on one OLT, with NO error code in enrichment, and a
                                      box-swap event the fault deliberately survives.
                                      Shape: a CLUSTER with no label -> access layer.
                                      (A content variant is also supported -> SOURCE.)

THE HONESTY INSTRUMENTS, built in from the start:
    Decoys    short, benign transients (a one-off home glitch, a prime-time load
              spike, an isolated reboot) that must NOT trigger a fault. They are
              recorded with is_decoy True and no true layer; any fire on them is a
              false positive.
    Healthy   the long stretches between events, where the engine must stay silent,
    stretches let the demo measure the baseline false-positive rate.

Real faults persist (dozens of intervals); decoys are short (one to three). That
persistence gap is the discriminator the engine will use. Faults push the magnitude
well above the healthy ceiling; decoys only tempt.

THE FOUR-FIELD BOUNDARY is preserved: the core stream stays four fields. Enrichment
is perturbed in step (freeze_duration, port_utilization, error_code) only so the
operator report is believable; the engine never reads it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from .core import (
    DemoConfig, EnrichmentRecord, GroundTruthLabel, Layer, RampProfile,
    SeededRandom, UseCase, make_core_record,
)
from .telemetry import ACCESS, CONTENT, TRANSPORT, IntervalTelemetry, TelemetryGenerator
from .topology import ServiceGraph


# ---------------------------------------------------------------------------
# Fault specification (internal) and its time profile
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FaultSpec:
    """One scheduled event: which homes are affected, on which subsystem edge, with
    what timing, ramp and magnitude. Decoys and real faults share this structure;
    is_decoy and true_layer distinguish them."""
    fault_id: str
    use_case: UseCase
    subsystem: str                 # ACCESS / TRANSPORT / CONTENT (which home edge)
    target_entity: Optional[str]   # the OLT / route / content the shape converges on
    affected_homes: Tuple[str, ...]
    onset: int
    end: int
    ramp: RampProfile
    ramp_intervals: int
    peak_magnitude: float
    is_decoy: bool
    has_error_code: bool
    error_code: Optional[str]
    true_layer: Optional[Layer]
    true_entity: Optional[str]
    box_swap_time: Optional[int]
    tipping_point: Optional[int]
    recommended_action: Optional[str]

    def delta(self, t: int) -> float:
        """The impairment delta this fault adds at interval t (0 outside its window).
        A box swap does not change the delta: the fault persists across it, which is
        exactly what proves the fault is not the box."""
        if t < self.onset or t >= self.end:
            return 0.0
        if self.ramp == RampProfile.SUDDEN:
            return self.peak_magnitude
        if t < self.onset + self.ramp_intervals:
            return self.peak_magnitude * (t - self.onset + 1) / self.ramp_intervals
        return self.peak_magnitude

    def to_ground_truth(self) -> GroundTruthLabel:
        return GroundTruthLabel(
            fault_id=self.fault_id, use_case=self.use_case, onset_time=self.onset,
            affected_entities=self.affected_homes, true_entity=self.true_entity,
            true_layer=self.true_layer, ramp=self.ramp, magnitude=self.peak_magnitude,
            is_decoy=self.is_decoy, has_explicit_error_code=self.has_error_code,
            box_swap_time=self.box_swap_time, tipping_point_time=self.tipping_point,
            recommended_action=self.recommended_action)


# ---------------------------------------------------------------------------
# Schedule construction - deterministic, scaled to the run length
# ---------------------------------------------------------------------------

def _pick_olt_in_region(graph: ServiceGraph, region: str,
                        exclude: set) -> Optional[str]:
    """The largest OLT in a region (most homes), excluding some, or None."""
    candidates = [(olt, len(homes)) for olt, homes in graph.stbs_by_olt.items()
                  if olt not in exclude
                  and graph.nodes[olt].region == region and homes]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1])[0]


def _largest_gaps(occupied: List[Tuple[int, int]], run: int, warmup: int,
                  k: int) -> List[Tuple[int, int]]:
    """The k widest healthy gaps (intervals covered by no event), past the warmup, so
    a decoy can be seated where it measures false positives in isolation."""
    busy = [False] * run
    for a, b in occupied:
        for t in range(max(0, a), min(b, run)):
            busy[t] = True
    gaps: List[Tuple[int, int]] = []
    t = max(0, warmup)
    while t < run:
        if not busy[t]:
            start = t
            while t < run and not busy[t]:
                t += 1
            gaps.append((start, t))
        else:
            t += 1
    gaps.sort(key=lambda g: -(g[1] - g[0]))
    return gaps[:k]


def build_fault_schedule(graph: ServiceGraph, config: DemoConfig) -> List[FaultSpec]:
    """Lay out the three use-case faults, the decoys, and (implicitly) the healthy
    stretches between them, deterministically and scaled to the run length."""
    rng = SeededRandom(config.seed).child("faults")
    R = config.run_intervals
    frac = lambda f: max(1, int(R * f))   # position as a fraction of the run
    specs: List[FaultSpec] = []
    used_olts: set = set()

    # --- UC1: gradual degradation on the largest OLT (clearest cluster) ---
    uc1_olt = max(graph.stbs_by_olt, key=lambda o: len(graph.stbs_by_olt[o]))
    used_olts.add(uc1_olt)
    uc1_homes = tuple(graph.stbs_by_olt[uc1_olt])
    uc1_central = graph.nodes[uc1_olt].identity.get("central_office", "")
    specs.append(FaultSpec(
        fault_id="F-UC1-OLT", use_case=UseCase.UC1_NETWORK_NODE, subsystem=ACCESS,
        target_entity=uc1_olt, affected_homes=uc1_homes,
        onset=frac(0.14), end=frac(0.34), ramp=RampProfile.GRADUAL,
        ramp_intervals=max(4, frac(0.05)), peak_magnitude=6.5, is_decoy=False,
        has_error_code=True, error_code="VIDEO_FREEZE", true_layer=Layer.ACCESS,
        true_entity=uc1_olt, box_swap_time=None, tipping_point=None,
        recommended_action="inspect aggregation port before complaints escalate"))

    # --- UC2: isolated home decline on a different OLT (peers must stay healthy) ---
    uc2_olt = None
    for olt in sorted(graph.stbs_by_olt, key=lambda o: -len(graph.stbs_by_olt[o])):
        if olt not in used_olts and len(graph.stbs_by_olt[olt]) >= 4:
            uc2_olt = olt
            break
    uc2_olt = uc2_olt or uc1_olt
    used_olts.add(uc2_olt)
    uc2_home = rng.choice(graph.stbs_by_olt[uc2_olt])
    uc2_region = graph.nodes[uc2_olt].region
    specs.append(FaultSpec(
        fault_id="F-UC2-HOME", use_case=UseCase.UC2_INDIVIDUAL, subsystem=ACCESS,
        target_entity=uc2_home, affected_homes=(uc2_home,),
        onset=frac(0.36), end=frac(0.58), ramp=RampProfile.GRADUAL,
        ramp_intervals=max(6, frac(0.08)), peak_magnitude=5.5, is_decoy=False,
        has_error_code=True, error_code="WIFI_LOW", true_layer=Layer.HOME,
        true_entity=uc2_home, box_swap_time=None, tipping_point=frac(0.47),
        recommended_action="proactive contact and gateway reconfiguration, no truck roll"))

    # --- UC3: invisible recurring fault on a small access segment, survives a swap ---
    # Prefer A Coruna (matches the operator example); else any unused OLT.
    uc3_olt = _pick_olt_in_region(graph, "A Coruna", used_olts) \
        or next((o for o in graph.stbs_by_olt if o not in used_olts), uc1_olt)
    used_olts.add(uc3_olt)
    seg_homes = tuple(graph.stbs_by_olt[uc3_olt][:min(9, len(graph.stbs_by_olt[uc3_olt]))])
    uc3_region = graph.nodes[uc3_olt].region
    specs.append(FaultSpec(
        fault_id="F-UC3-SEG", use_case=UseCase.UC3_INVISIBLE, subsystem=ACCESS,
        target_entity=uc3_olt, affected_homes=seg_homes,
        onset=frac(0.62), end=frac(0.90), ramp=RampProfile.GRADUAL,
        ramp_intervals=max(4, frac(0.04)), peak_magnitude=5.0, is_decoy=False,
        has_error_code=False, error_code=None, true_layer=Layer.ACCESS,
        true_entity=uc3_olt, box_swap_time=frac(0.74), tipping_point=None,
        recommended_action="investigate access segment, stop dispatching box swaps"))

    # --- Decoys (honesty instruments) - short transients that must NOT fire ---
    # Seat each decoy in a healthy gap between the real faults (past a nominal warmup),
    # so it measures false positives in isolation rather than overlapping a real fault.
    occupied = [(s.onset, s.end) for s in specs]
    nominal_warmup = max(3, min(20, R // 12))
    gaps = _largest_gaps(occupied, R, nominal_warmup, k=3)
    # pad with the tail gap if fewer than three were found
    while len(gaps) < 3:
        gaps.append((max(0, R - 3), R))

    def gap_center(i: int, width: int) -> int:
        a, b = gaps[i % len(gaps)]
        c0 = a + max(0, (b - a - width) // 2)
        return min(c0, max(a, b - width))

    # 1) load spike: many homes, brief
    spike_at = gap_center(0, 2)
    spike_sample = tuple(rng.sample(graph.stb_ids, min(40, len(graph.stb_ids))))
    specs.append(FaultSpec(
        fault_id="D-PRIME-SPIKE", use_case=UseCase.DECOY, subsystem=ACCESS,
        target_entity=None, affected_homes=spike_sample,
        onset=spike_at, end=spike_at + 2, ramp=RampProfile.SUDDEN, ramp_intervals=1,
        peak_magnitude=1.8, is_decoy=True, has_error_code=False, error_code=None,
        true_layer=None, true_entity=None, box_swap_time=None, tipping_point=None,
        recommended_action=None))

    # 2) one-off home glitch: a single home, a single interval
    glitch_at = gap_center(1, 1)
    glitch_home = rng.choice(graph.stb_ids)
    specs.append(FaultSpec(
        fault_id="D-GLITCH", use_case=UseCase.DECOY, subsystem=ACCESS,
        target_entity=None, affected_homes=(glitch_home,),
        onset=glitch_at, end=glitch_at + 1, ramp=RampProfile.SUDDEN, ramp_intervals=1,
        peak_magnitude=4.0, is_decoy=True, has_error_code=False, error_code=None,
        true_layer=None, true_entity=None, box_swap_time=None, tipping_point=None,
        recommended_action=None))

    # 3) isolated reboot: a single home, brief, low magnitude
    reboot_at = gap_center(2, 1)
    reboot_home = rng.choice(graph.stb_ids)
    specs.append(FaultSpec(
        fault_id="D-REBOOT", use_case=UseCase.DECOY, subsystem=ACCESS,
        target_entity=None, affected_homes=(reboot_home,),
        onset=reboot_at, end=reboot_at + 1, ramp=RampProfile.SUDDEN, ramp_intervals=1,
        peak_magnitude=2.2, is_decoy=True, has_error_code=False, error_code=None,
        true_layer=None, true_entity=None, box_swap_time=None, tipping_point=None,
        recommended_action=None))

    return specs


# ---------------------------------------------------------------------------
# The injector - perturbs healthy telemetry, emits ground truth
# ---------------------------------------------------------------------------

class FaultInjector:
    """Wraps a TelemetryGenerator and injects the scheduled faults. interval(t)
    returns the FAULTED telemetry for interval t (healthy plus the active deltas),
    deterministically. ground_truth_labels() returns the recorded answer key."""

    def __init__(self, graph: ServiceGraph, config: DemoConfig) -> None:
        self.graph = graph
        self.config = config
        self.generator = TelemetryGenerator(graph, config)
        self.schedule: List[FaultSpec] = build_fault_schedule(graph, config)

    def ground_truth_labels(self) -> List[GroundTruthLabel]:
        return [s.to_ground_truth() for s in self.schedule]

    def real_faults(self) -> List[GroundTruthLabel]:
        return [s.to_ground_truth() for s in self.schedule if not s.is_decoy]

    def decoys(self) -> List[GroundTruthLabel]:
        return [s.to_ground_truth() for s in self.schedule if s.is_decoy]

    def _home_edge_dst(self, spec: FaultSpec, home: str) -> str:
        m = self.graph.stb_membership[home]
        return {ACCESS: m.olt_id, TRANSPORT: m.route_id, CONTENT: m.content_id}[spec.subsystem]

    def _perturb_home_enrichment(self, enr: Dict[str, EnrichmentRecord], spec: FaultSpec,
                                 home: str, d: float, t: int) -> None:
        """Raise the home's report fields in step with the fault, for a believable
        operator line. Never read by the engine."""
        rec = enr.get(home)
        if rec is None:
            return
        f = rec.fields
        f["freeze_duration"] = round(f.get("freeze_duration", 0.0) + d, 3)
        # the invisible fault (UC3) deliberately carries NO explicit error code
        if spec.has_error_code and not spec.is_decoy:
            f["error_code"] = spec.error_code
        if spec.use_case == UseCase.UC2_INDIVIDUAL:
            f["wifi_snr"] = round(max(8.0, 30.0 - 4.0 * d), 2)
            f["wan_packet_loss"] = round(min(15.0, 0.5 * d), 3)
        if spec.box_swap_time is not None and t >= spec.box_swap_time:
            f["stb_swapped"] = True   # the swap happened, yet impairment persists

    def _perturb_node_enrichment(self, enr: Dict[str, EnrichmentRecord], spec: FaultSpec,
                                 d: float, t: int) -> None:
        """Raise the faulted infrastructure node's own report fields."""
        if spec.target_entity is None or spec.is_decoy:
            return
        rec = enr.get(spec.target_entity)
        if rec is None:
            return
        f = rec.fields
        if spec.subsystem == ACCESS and "port_utilization" in f:
            f["port_utilization"] = round(min(0.99, f["port_utilization"] + 0.06 * d), 3)
            f["fec_errors"] = int(f.get("fec_errors", 0) + 50 * d)
        elif spec.subsystem == CONTENT and "segment_failures" in f:
            f["segment_failures"] = int(f.get("segment_failures", 0) + 20 * d)
            f["encoder_dropped_frm"] = int(f.get("encoder_dropped_frm", 0) + 10 * d)
        elif spec.subsystem == TRANSPORT and "transport_load" in f:
            f["transport_load"] = round(min(0.99, f["transport_load"] + 0.05 * d), 3)

    def interval(self, t: int) -> IntervalTelemetry:
        """Faulted telemetry for interval t: the healthy interval with every active
        fault's delta applied to the relevant core edges and enrichment fields."""
        it = self.generator.interval(t)
        core = list(it.core)
        for spec in self.schedule:
            d = spec.delta(t)
            if d <= 0.0:
                continue
            for home in spec.affected_homes:
                dst = self._home_edge_dst(spec, home)
                idx = it.core_index.get((home, dst), -1)
                if idx >= 0:
                    old = core[idx]
                    core[idx] = make_core_record(old.entity_src, old.entity_dst, t,
                                                 old.magnitude + d)
                self._perturb_home_enrichment(it.enrichment, spec, home, d, t)
            self._perturb_node_enrichment(it.enrichment, spec, d, t)
        return IntervalTelemetry(timestamp=t, core=core, enrichment=it.enrichment,
                                 core_index=it.core_index)

    def stream(self) -> Iterator[IntervalTelemetry]:
        for t in range(self.config.run_intervals):
            yield self.interval(t)
