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
from typing import Dict, List, Mapping, Optional, Tuple

from .contracts import (
    ActionCode, DemoConfig, Diagnosis, Layer, Msg, SHAPE_TO_LAYER, Score, Shape, UseCase,
)
from .messages import CATALOGUE_EN, render as render_msg
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

    def render(self, cat: Optional[Mapping[str, str]] = None) -> str:
        """The scorecard as plain text.

        Takes a catalogue so the web console can show it in Spanish; defaults to English
        for the terminal and the HTML export, which have no request to read a language
        from. Every number is formatted here and passed in as a fact - the catalogue only
        ever supplies wording.
        """
        cat = CATALOGUE_EN if cat is None else cat

        def say(key: str, **params) -> str:
            return render_msg(Msg(key, params), cat)

        lines = [say("scorecard.heading"), ""]
        for s in self.per_use_case:
            lines.append(f"{s.use_case.value}:")
            lines.append("  " + say("scorecard.detected",
                                    n=s.n_detected, total=s.n_faults))
            if s.mean_lead_time_intervals is not None:
                lines.append("  " + say("scorecard.lead_time",
                                        intervals=f"{s.mean_lead_time_intervals:.0f}",
                                        minutes=self._mins(s.mean_lead_time_intervals)))
            lines.append("  " + say("scorecard.localization",
                                    pct=f"{s.localization_accuracy:.0%}"))
            lines.append("  " + say("scorecard.layer_attribution",
                                    pct=f"{s.layer_attribution_accuracy:.0%}"))
            if s.box_swap_discrimination is not None:
                lines.append("  " + say("scorecard.box_swap",
                                        pct=f"{s.box_swap_discrimination:.0%}"))
            lines.append("  " + say("scorecard.action_correctness",
                                    pct=f"{s.action_correctness:.0%}"))
            if s.note_msg is not None or s.note:
                detail = render_msg(s.note_msg, cat) if s.note_msg else s.note
                lines.append("  " + say("scorecard.note", note=detail))
            lines.append("")
        lines.append(say("scorecard.false_positive_rate",
                         pct=f"{self.false_positive_rate:.1%}",
                         spurious=self.n_spurious_intervals,
                         total=self.n_non_fault_intervals))
        lines.append(say("scorecard.decoys_fired",
                         fired=self.n_decoys_fired, total=self.n_decoys))
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
        note_msg = Msg("score.note.not_detected", {})

        if matched:
            first_t = min(t for t, _ in matched)
            lead = float(surfacing - first_t)
            # settled verdict: the element named most often across the fault's life
            settled_entity, _ = Counter(d.entity_id for _, d in matched).most_common(1)[0]
            rep = next(d for _, d in matched if d.entity_id == settled_entity)
            localization = 1.0 if settled_entity == spec.true_entity else 0.0
            layer_acc = 1.0 if rep.layer == spec.true_layer else 0.0
            action_acc = 1.0 if self._action_ok(rep.shape, spec.true_layer,
                                                 rep.action_code) else 0.0
            if spec.use_case == UseCase.UC3_INVISIBLE:
                # the box would have been spared: attributed off the home, no box swap
                no_box = not (rep.action_code and rep.action_code.is_box_swap)
                box_swap = 1.0 if (rep.layer != Layer.HOME and no_box) else 0.0
            note_msg = Msg("score.note.detected",
                           {"interval": first_t, "entity": settled_entity,
                            "layer": rep.layer.value if rep.layer else "?",
                            "shape": rep.shape.value, "lead": f"{lead:.0f}",
                            "surfacing": surfacing})

        return Score(
            use_case=spec.use_case, n_faults=1, n_detected=n_detected,
            mean_lead_time_intervals=lead, localization_accuracy=localization,
            layer_attribution_accuracy=layer_acc, box_swap_discrimination=box_swap,
            false_positive_rate=0.0, action_correctness=action_acc,
            note=render_msg(note_msg), note_msg=note_msg)

    @staticmethod
    def _action_ok(shape: Shape, true_layer: Layer, action: Optional[ActionCode]) -> bool:
        """Action correctness by category: the action implied by the engine's shape
        should be appropriate for the true layer (a network-side action for an access
        fault, a customer-side action for a home fault, and so on).

        This reads the action CODE, never its wording. It used to ask whether the
        recommendation contained the word "box", which measured the language the demo
        happened to be written in: the moment the console spoke Spanish, the box-swap
        check would have passed on every input while proving nothing.
        """
        implied = SHAPE_TO_LAYER.get(shape)
        if implied != true_layer:
            return False
        # an access fault must never be answered with a box swap
        if true_layer == Layer.ACCESS and action is not None and action.is_box_swap:
            return False
        return True
