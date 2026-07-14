"""
Module 6 - Scoring harness.

This is where the demo earns its credibility. It runs the engine over the faulted
stream, compares every diagnosis to the answer key Module 3 records, and reports the
measured numbers the demo promises. There are NO pre-committed thresholds: the
harness reports what was measured, against references that are defined structurally,
not by a magic number.

The measures, per use case:
  detection lead time   how many intervals before the fault would surface (its
                        plateau, or for the isolated decline its recorded tipping
                        point) the engine first flagged it. Positive means early.
  localization accuracy did the engine's settled verdict name the exact true element.
  layer attribution     did the settled verdict place it in the true layer.
  box-swap discrimination (the invisible fault) did the engine attribute to a
                        non-home layer and recommend a network-side action, so the
                        futile box swap would have been avoided.
  action correctness    judged by category against the true layer (a network-side
                        action for an access fault, a customer-side action for a home
                        fault), not by exact wording.
And globally:
  false-positive rate   across every interval where no real fault is active (the
                        decoys and the long healthy stretches), how often the engine
                        fired a detection it should not have.

The settled verdict for a fault is the element the engine named most often across the
fault's life, so a brief ramp-edge read does not stand in for the engine's real
conclusion. Every number is traceable to the ground truth and the collected
diagnoses, so the harness can be checked by hand.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .contracts import (
    DemoConfig, Diagnosis, Layer, SHAPE_TO_LAYER, Score, Shape, UseCase,
)
from .fault_injection import FaultInjector, FaultSpec
from .si_engine import StructuralIntelligenceEngine


# ---------------------------------------------------------------------------
# The aggregated report
# ---------------------------------------------------------------------------

@dataclass
class ScoreReport:
    """The full scorecard: one Score per real use case, plus the global
    false-positive accounting and an overall summary."""
    per_use_case: List[Score]
    false_positive_rate: float
    n_non_fault_intervals: int
    n_spurious_intervals: int
    n_decoys: int
    n_decoys_fired: int
    interval_seconds: int
    notes: List[str] = field(default_factory=list)

    def _mins(self, intervals: Optional[float]) -> str:
        if intervals is None:
            return "n/a"
        return f"{intervals * self.interval_seconds / 60:.0f} min"

    def render(self) -> str:
        lines = ["Structural Intelligence demo scorecard (measured values, no preset thresholds)",
                 ""]
        for s in self.per_use_case:
            lines.append(f"{s.use_case.value}:")
            lines.append(f"  detected: {s.n_detected}/{s.n_faults}")
            if s.mean_lead_time_intervals is not None:
                lines.append(f"  detection lead time: {s.mean_lead_time_intervals:.0f} intervals "
                             f"({self._mins(s.mean_lead_time_intervals)}) before the fault would surface")
            lines.append(f"  localization accuracy: {s.localization_accuracy:.0%}")
            lines.append(f"  layer attribution: {s.layer_attribution_accuracy:.0%}")
            if s.box_swap_discrimination is not None:
                lines.append(f"  box-swap discrimination: {s.box_swap_discrimination:.0%} "
                             f"(the box swap would have been avoided)")
            lines.append(f"  action correctness: {s.action_correctness:.0%}")
            if s.note:
                lines.append(f"  note: {s.note}")
            lines.append("")
        lines.append(f"false-positive rate: {self.false_positive_rate:.1%} "
                     f"({self.n_spurious_intervals} spurious of {self.n_non_fault_intervals} "
                     f"no-fault intervals)")
        lines.append(f"decoys that fired: {self.n_decoys_fired}/{self.n_decoys}")
        for n in self.notes:
            lines.append(n)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The harness
# ---------------------------------------------------------------------------

class ScoringHarness:
    """Runs the engine over the faulted stream and scores it against ground truth."""

    def __init__(self, config: DemoConfig) -> None:
        self.config = config

    # ----- running the engine to collect diagnoses -----

    def collect_diagnoses(self, injector: FaultInjector,
                          engine: StructuralIntelligenceEngine) -> Dict[int, List[Diagnosis]]:
        per_interval: Dict[int, List[Diagnosis]] = {}
        for t in range(self.config.run_intervals):
            per_interval[t] = engine.observe_and_diagnose(t, injector.interval(t).core)
        return per_interval

    def evaluate(self, injector: FaultInjector,
                 engine: StructuralIntelligenceEngine) -> ScoreReport:
        return self.score(injector, self.collect_diagnoses(injector, engine))

    # ----- the pure scoring -----

    def score(self, injector: FaultInjector,
              per_interval: Dict[int, List[Diagnosis]]) -> ScoreReport:
        real = [s for s in injector.schedule if not s.is_decoy]
        decoys = [s for s in injector.schedule if s.is_decoy]
        real_windows = [(s.onset, s.end) for s in real]

        per_use_case = [self._score_fault(s, per_interval) for s in real]

        # global false positives: any detection in an interval with no real fault active
        spurious = 0
        non_fault = 0
        for t in range(self.config.run_intervals):
            if any(a <= t < b for a, b in real_windows):
                continue
            non_fault += 1
            if any(d.detected for d in per_interval.get(t, [])):
                spurious += 1
        fp_rate = (spurious / non_fault) if non_fault else 0.0

        # decoys that fired: a detection during a decoy window (no real fault overlaps,
        # since decoys are seated in healthy gaps)
        decoys_fired = 0
        for dspec in decoys:
            if any(d.detected for t in range(dspec.onset, dspec.end)
                   for d in per_interval.get(t, [])):
                decoys_fired += 1

        return ScoreReport(
            per_use_case=per_use_case, false_positive_rate=fp_rate,
            n_non_fault_intervals=non_fault, n_spurious_intervals=spurious,
            n_decoys=len(decoys), n_decoys_fired=decoys_fired,
            interval_seconds=self.config.interval_seconds)

    # ----- scoring one fault -----

    def _matches(self, d: Diagnosis, spec: FaultSpec) -> bool:
        """Does this detected diagnosis correspond to this fault: by naming its true
        element, by naming one of its affected homes, or by its signature overlapping
        the fault's affected set."""
        if not d.detected:
            return False
        if d.entity_id == spec.true_entity:
            return True
        if d.entity_id in spec.affected_homes:
            return True
        examined = set(d.evidence.provenance.entities_examined) if d.evidence else set()
        return bool(examined & set(spec.affected_homes))

    def _score_fault(self, spec: FaultSpec, per_interval: Dict[int, List[Diagnosis]]) -> Score:
        matched: List[Tuple[int, Diagnosis]] = []
        for t in range(spec.onset, min(spec.end, self.config.run_intervals)):
            for d in per_interval.get(t, []):
                if self._matches(d, spec):
                    matched.append((t, d))

        n_detected = 1 if matched else 0
        # surfacing reference: the recorded tipping point, else the ramp plateau
        surfacing = spec.tipping_point if spec.tipping_point is not None \
            else spec.onset + spec.ramp_intervals
        lead = None
        localization = 0.0
        layer_acc = 0.0
        action_acc = 0.0
        box_swap = None
        note = "not detected"

        if matched:
            first_t = min(t for t, _ in matched)
            lead = float(surfacing - first_t)
            # settled verdict: the element named most often across the fault's life
            settled_entity, _ = Counter(d.entity_id for _, d in matched).most_common(1)[0]
            rep = next(d for _, d in matched if d.entity_id == settled_entity)
            localization = 1.0 if settled_entity == spec.true_entity else 0.0
            layer_acc = 1.0 if rep.layer == spec.true_layer else 0.0
            action_acc = 1.0 if self._action_ok(rep.shape, spec.true_layer,
                                                 rep.recommended_action) else 0.0
            if spec.use_case == UseCase.UC3_INVISIBLE:
                # the box would have been spared: attributed off the home, no box swap
                no_box = "box" not in (rep.recommended_action or "").lower()
                box_swap = 1.0 if (rep.layer != Layer.HOME and no_box) else 0.0
            note = (f"detected at interval {first_t}, named {settled_entity} "
                    f"({rep.layer.value}/{rep.shape.value}), "
                    f"lead {lead:.0f} intervals to surfacing at {surfacing}")

        return Score(
            use_case=spec.use_case, n_faults=1, n_detected=n_detected,
            mean_lead_time_intervals=lead, localization_accuracy=localization,
            layer_attribution_accuracy=layer_acc, box_swap_discrimination=box_swap,
            false_positive_rate=0.0, action_correctness=action_acc, note=note)

    @staticmethod
    def _action_ok(shape: Shape, true_layer: Layer, action: Optional[str]) -> bool:
        """Action correctness by category: the action implied by the engine's shape
        should be appropriate for the true layer (a network-side action for an access
        fault, a customer-side action for a home fault, and so on)."""
        implied = SHAPE_TO_LAYER.get(shape)
        if implied != true_layer:
            return False
        # an access fault must never be answered with a box swap
        if true_layer == Layer.ACCESS and "box" in (action or "").lower():
            return False
        return True
