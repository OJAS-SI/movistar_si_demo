"""
Standalone test for Module 6 - Scoring harness.

    python tests/test_module6_scoring.py     (no dependencies)
    pytest tests/test_module6_scoring.py

Two kinds of check. First, the real engine run is scored end to end and must score
cleanly. Second, hand-built diagnoses against the real ground truth confirm each
metric is computed correctly in isolation: lead time is surfacing minus first
detection, a wrong layer is caught, a mislocalized element is caught, a missed fault
scores zero detected, a fired decoy raises the false-positive count, and the box-swap
metric flips when the engine wrongly blames the box.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import traceback

import si_core.contracts as c
from si_core.topology import build_service_graph
from si_core.fault_injection import FaultInjector
from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
from si_core.scoring import ScoringHarness, ScoreReport


def _injector(cfg=None):
    cfg = cfg or c.tiny_config()
    return cfg, build_service_graph(cfg), FaultInjector(build_service_graph(cfg), cfg)


def _spec(inj, fid):
    return next(s for s in inj.schedule if s.fault_id == fid)


def _uc(report, use_case):
    return next(s for s in report.per_use_case if s.use_case == use_case)


def _mk_diag(t, entity, layer, shape, action="inspect the access node and its aggregation",
             examined=(), detected=True, abstained=False):
    prov = c.Provenance(interval_start=max(0, t - 3), interval_end=t,
                        entities_examined=tuple(examined), note="test")
    ev = c.Evidence(claim="c", supporting=("s",), check="ck", provenance=prov)
    return c.Diagnosis(timestamp=t, detected=detected, abstained=abstained, entity_id=entity,
                       layer=layer, shape=shape, confidence=0.9, trajectory=None,
                       evidence=ev, recommended_action=action)


# ---------------------------------------------------------------------------
# 1. The real engine run scores cleanly
# ---------------------------------------------------------------------------

def test_real_run_scores_perfectly():
    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    report = ScoringHarness(cfg).evaluate(inj, eng)

    for s in report.per_use_case:
        assert s.n_detected == 1, f"{s.use_case} not detected"
        assert s.localization_accuracy == 1.0, f"{s.use_case} localization"
        assert s.layer_attribution_accuracy == 1.0, f"{s.use_case} layer"
        assert s.action_correctness == 1.0, f"{s.use_case} action"
        assert s.mean_lead_time_intervals is not None and s.mean_lead_time_intervals >= 0
    uc3 = _uc(report, c.UseCase.UC3_INVISIBLE)
    assert uc3.box_swap_discrimination == 1.0
    assert report.false_positive_rate == 0.0
    assert report.n_decoys_fired == 0


# ---------------------------------------------------------------------------
# 2. Lead time
# ---------------------------------------------------------------------------

def test_lead_time_is_surfacing_minus_first_detection():
    cfg, g, inj = _injector()
    s = _spec(inj, "F-UC1-OLT")
    surfacing = s.tipping_point if s.tipping_point is not None else s.onset + s.ramp_intervals
    detect_at = s.onset + 1
    pi = {t: [_mk_diag(t, s.true_entity, c.Layer.ACCESS, c.Shape.CLUSTER,
                       examined=s.affected_homes)]
          for t in range(detect_at, s.end)}
    report = ScoringHarness(cfg).score(inj, pi)
    uc1 = _uc(report, c.UseCase.UC1_NETWORK_NODE)
    assert uc1.mean_lead_time_intervals == float(surfacing - detect_at)


# ---------------------------------------------------------------------------
# 3. Localization and layer errors are caught
# ---------------------------------------------------------------------------

def test_wrong_layer_is_caught():
    cfg, g, inj = _injector()
    s = _spec(inj, "F-UC1-OLT")
    # right element, wrong layer (core instead of access)
    pi = {t: [_mk_diag(t, s.true_entity, c.Layer.CORE, c.Shape.PATH,
                       action="investigate the core transport route", examined=s.affected_homes)]
          for t in range(s.onset + 1, s.end)}
    uc1 = _uc(ScoringHarness(cfg).score(inj, pi), c.UseCase.UC1_NETWORK_NODE)
    assert uc1.localization_accuracy == 1.0   # the element was named
    assert uc1.layer_attribution_accuracy == 0.0  # but the layer was wrong
    assert uc1.action_correctness == 0.0      # and the action no longer fits


def test_mislocalized_element_is_caught():
    cfg, g, inj = _injector()
    s = _spec(inj, "F-UC1-OLT")
    wrong_home = s.affected_homes[0]   # names a home, not the OLT
    pi = {t: [_mk_diag(t, wrong_home, c.Layer.HOME, c.Shape.SINGLE,
                       action="proactive customer contact", examined=(wrong_home,))]
          for t in range(s.onset + 1, s.end)}
    uc1 = _uc(ScoringHarness(cfg).score(inj, pi), c.UseCase.UC1_NETWORK_NODE)
    assert uc1.n_detected == 1            # something overlapping the fault was flagged
    assert uc1.localization_accuracy == 0.0   # but it named the wrong element


# ---------------------------------------------------------------------------
# 4. A missed fault
# ---------------------------------------------------------------------------

def test_missed_fault_scores_zero_detected():
    cfg, g, inj = _injector()
    # no diagnoses at all
    report = ScoringHarness(cfg).score(inj, {})
    for s in report.per_use_case:
        assert s.n_detected == 0
        assert s.mean_lead_time_intervals is None
        assert s.localization_accuracy == 0.0


# ---------------------------------------------------------------------------
# 5. False positives - decoys and healthy intervals
# ---------------------------------------------------------------------------

def test_fired_decoy_raises_false_positive():
    cfg, g, inj = _injector()
    decoy = next(s for s in inj.schedule if s.is_decoy)
    home = decoy.affected_homes[0]
    olt = g.stb_membership[home].olt_id
    # a spurious detection during the decoy window
    pi = {decoy.onset: [_mk_diag(decoy.onset, olt, c.Layer.ACCESS, c.Shape.CLUSTER,
                                 examined=(home,))]}
    report = ScoringHarness(cfg).score(inj, pi)
    assert report.n_decoys_fired >= 1
    assert report.false_positive_rate > 0.0
    assert report.n_spurious_intervals >= 1


def test_clean_run_has_zero_false_positive():
    cfg, g, inj = _injector()
    report = ScoringHarness(cfg).score(inj, {})   # no detections anywhere
    assert report.false_positive_rate == 0.0
    assert report.n_decoys_fired == 0


# ---------------------------------------------------------------------------
# 6. Box-swap discrimination
# ---------------------------------------------------------------------------

def test_box_swap_passes_when_attributed_to_access():
    cfg, g, inj = _injector()
    s = _spec(inj, "F-UC3-SEG")
    pi = {t: [_mk_diag(t, s.true_entity, c.Layer.ACCESS, c.Shape.CLUSTER,
                       action="investigate access segment", examined=s.affected_homes)]
          for t in range(s.onset + 1, s.end)}
    uc3 = _uc(ScoringHarness(cfg).score(inj, pi), c.UseCase.UC3_INVISIBLE)
    assert uc3.box_swap_discrimination == 1.0


def test_box_swap_flips_when_box_is_blamed():
    cfg, g, inj = _injector()
    s = _spec(inj, "F-UC3-SEG")
    home = s.affected_homes[0]
    # the engine wrongly blames the home/box
    pi = {t: [_mk_diag(t, home, c.Layer.HOME, c.Shape.SINGLE,
                       action="swap the set-top box", examined=(home,))]
          for t in range(s.onset + 1, s.end)}
    uc3 = _uc(ScoringHarness(cfg).score(inj, pi), c.UseCase.UC3_INVISIBLE)
    assert uc3.box_swap_discrimination == 0.0


# ---------------------------------------------------------------------------
# 7. Action correctness by category
# ---------------------------------------------------------------------------

def test_action_correctness_rejects_box_swap_for_access():
    assert ScoringHarness._action_ok(c.Shape.CLUSTER, c.Layer.ACCESS,
                                     "inspect the access node") is True
    assert ScoringHarness._action_ok(c.Shape.CLUSTER, c.Layer.ACCESS,
                                     "swap the box") is False
    # right category for a home fault
    assert ScoringHarness._action_ok(c.Shape.SINGLE, c.Layer.HOME,
                                     "proactive customer contact") is True
    # wrong category: a single/home action for an access fault
    assert ScoringHarness._action_ok(c.Shape.SINGLE, c.Layer.ACCESS, "contact") is False


# ---------------------------------------------------------------------------
# 8. Render and determinism
# ---------------------------------------------------------------------------

def test_render_contains_all_metrics():
    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    text = ScoringHarness(cfg).evaluate(inj, eng).render()
    for token in ["detection lead time", "localization accuracy", "layer attribution",
                  "box-swap discrimination", "action correctness", "false-positive rate"]:
        assert token in text, f"scorecard missing '{token}'"


def test_scoring_is_deterministic():
    cfg = c.tiny_config()
    def run():
        g = build_service_graph(cfg)
        inj = FaultInjector(g, cfg)
        eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
        return ScoringHarness(cfg).evaluate(inj, eng)
    a, b = run(), run()
    assert [(_s.use_case, _s.localization_accuracy, _s.mean_lead_time_intervals)
            for _s in a.per_use_case] == \
           [(_s.use_case, _s.localization_accuracy, _s.mean_lead_time_intervals)
            for _s in b.per_use_case]
    assert a.false_positive_rate == b.false_positive_rate


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    failures = []
    for t in tests:
        try:
            t(); passed += 1; print(f"  PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1; failures.append((t.__name__, traceback.format_exc()))
            print(f"  FAIL  {t.__name__}: {exc}")
    print(f"\nModule 6 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
