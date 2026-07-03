"""
Standalone test for Module 4 - The Structural Intelligence engine.

    python tests/test_module4_si_engine.py     (no dependencies)
    pytest tests/test_module4_si_engine.py

This test rehearses the demo's success criteria directly, scored against the ground
truth Module 3 produces: the engine detects each injected fault early, names the
correct element and its true layer, proves UC3 is not the box and survives the swap,
fires on no decoy or healthy interval, abstains rather than guessing when the
evidence is ambiguous, and consumes only the four-field stream.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import traceback

import si_demo.core as c
from si_demo.topology import build_service_graph
from si_demo.fault_injection import FaultInjector
from si_demo.si_engine import (
    EngineParams, NetworkMap, StructuralIntelligenceEngine,
)


def _run(cfg=None):
    cfg = cfg or c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    per_interval = {t: eng.observe_and_diagnose(t, inj.interval(t).core)
                    for t in range(cfg.run_intervals)}
    return g, cfg, inj, eng, per_interval


def _spec(inj, fid):
    return next(s for s in inj.schedule if s.fault_id == fid)


def _first_detection_of(per_interval, entity):
    for t in sorted(per_interval):
        for d in per_interval[t]:
            if d.detected and d.entity_id == entity:
                return t, d
    return None, None


# ---------------------------------------------------------------------------
# 1. UC1 - a node failure caught early, named, attributed to access
# ---------------------------------------------------------------------------

def test_uc1_detected_named_and_attributed():
    g, cfg, inj, eng, pi = _run()
    s = _spec(inj, "F-UC1-OLT")
    t, d = _first_detection_of(pi, s.target_entity)
    assert d is not None, "UC1 OLT was never detected"
    assert d.layer == c.Layer.ACCESS and d.shape == c.Shape.CLUSTER
    # caught early: at or before the fault reaches its plateau (the complaint wave)
    plateau = s.onset + s.ramp_intervals
    assert t <= plateau + 1, f"UC1 detected at {t}, later than plateau {plateau}"
    assert t >= s.onset, "detected before the fault even began"


# ---------------------------------------------------------------------------
# 2. UC2 - an isolated decline, named to the home, peers confirmed healthy
# ---------------------------------------------------------------------------

def test_uc2_detected_as_isolated_home():
    g, cfg, inj, eng, pi = _run()
    s = _spec(inj, "F-UC2-HOME")
    home = s.affected_homes[0]
    t, d = _first_detection_of(pi, home)
    assert d is not None, "UC2 home was never detected"
    assert d.layer == c.Layer.HOME and d.shape == c.Shape.SINGLE
    # the receipt's check should rest on peer-health (isolation)
    assert "peers" in d.evidence.check or "isolation" in d.evidence.claim.lower()


# ---------------------------------------------------------------------------
# 3. UC3 - invisible fault localized to access, proven not the box, survives swap
# ---------------------------------------------------------------------------

def test_uc3_localized_to_access_not_the_box():
    g, cfg, inj, eng, pi = _run()
    s = _spec(inj, "F-UC3-SEG")
    t, d = _first_detection_of(pi, s.target_entity)
    assert d is not None, "UC3 segment was never detected"
    # attributed to access (a shared cluster), NOT to the home/box
    assert d.layer == c.Layer.ACCESS and d.shape == c.Shape.CLUSTER
    # the recommended action is network-side, not a box swap
    assert "box" not in (d.recommended_action or "").lower()


def test_uc3_detection_persists_across_box_swap():
    g, cfg, inj, eng, pi = _run()
    s = _spec(inj, "F-UC3-SEG")
    swap = s.box_swap_time
    # the engine still names the access node as a cluster after the swap
    after = [d for t in range(swap, s.end) for d in pi[t]
             if d.detected and d.entity_id == s.target_entity and d.layer == c.Layer.ACCESS]
    assert after, "UC3 attribution did not persist across the box swap"


# ---------------------------------------------------------------------------
# 4. Honesty - no false positives on decoys or healthy intervals
# ---------------------------------------------------------------------------

def test_no_detection_on_decoy_only_intervals():
    g, cfg, inj, eng, pi = _run()
    # intervals where a decoy is active but no real fault is
    active_real = set()
    active_decoy = set()
    for sp in inj.schedule:
        for t in range(sp.onset, sp.end):
            (active_decoy if sp.is_decoy else active_real).add(t)
    decoy_only = active_decoy - active_real
    assert decoy_only, "expected some decoy-only intervals"
    for t in decoy_only:
        assert not any(d.detected for d in pi[t]), (
            f"a decoy at interval {t} wrongly triggered a detection")


def test_no_detection_on_healthy_intervals():
    g, cfg, inj, eng, pi = _run()
    active = set()
    for sp in inj.schedule:
        active.update(range(sp.onset, sp.end))
    healthy = [t for t in range(cfg.run_intervals) if t not in active]
    for t in healthy:
        assert not any(d.detected for d in pi[t]), (
            f"a detection fired on healthy interval {t}")


# ---------------------------------------------------------------------------
# 5. The competence boundary - abstain rather than guess
# ---------------------------------------------------------------------------

def test_engine_can_abstain_on_a_forming_cluster_edge():
    # Construct the leading edge of a cluster: one home over the dwell, several of its
    # access-node peers rising. The engine must defer, not call a lone home.
    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    nm = NetworkMap(g)
    eng = StructuralIntelligenceEngine(nm, cfg, EngineParams(warmup_intervals=3))
    olt = max(g.stbs_by_olt, key=lambda o: len(g.stbs_by_olt[o]))
    homes = g.stbs_by_olt[olt][:6]
    # warm up healthy
    for t in range(4):
        recs = [c.make_core_record(h, olt, t, 0.5) for h in g.stbs_by_olt[olt]]
        eng.observe_and_diagnose(t, recs)
    # one home sustained over dwell, peers rising (elevated but newer)
    saw_abstain = False
    for t in range(4, 12):
        recs = []
        for i, h in enumerate(g.stbs_by_olt[olt]):
            if h == homes[0]:
                recs.append(c.make_core_record(h, olt, t, 6.0))           # sustained
            elif h in homes[1:5] and t >= 9:
                recs.append(c.make_core_record(h, olt, t, 6.0))           # peers just rising
            else:
                recs.append(c.make_core_record(h, olt, t, 0.5))
        for d in eng.observe_and_diagnose(t, recs):
            if d.abstained:
                saw_abstain = True
    assert saw_abstain, "engine did not abstain at a forming-cluster edge"


def test_abstention_carries_a_receipt_and_no_entity():
    g, cfg, inj, eng, pi = _run()
    abstentions = [d for t in pi for d in pi[t] if d.abstained]
    # our run produces abstentions at the UC3 ramp edge
    assert abstentions, "expected at least one abstention in the run"
    for d in abstentions:
        assert d.entity_id is None and d.layer is None
        assert d.evidence is not None and d.evidence.claim


# ---------------------------------------------------------------------------
# 6. The four-field boundary, receipts, confidence, determinism
# ---------------------------------------------------------------------------

def test_engine_rejects_enrichment_at_its_entry():
    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    enr = c.EnrichmentRecord(entity_id="x", timestamp=0, entity_type=c.EntityType.STB,
                             layer=c.Layer.HOME, fields={"error_code": "X"})
    try:
        eng.observe_and_diagnose(0, [enr])
    except TypeError:
        return
    raise AssertionError("engine must reject enrichment at its four-field entry")


def test_every_detection_carries_a_full_receipt():
    g, cfg, inj, eng, pi = _run()
    dets = [d for t in pi for d in pi[t] if d.detected]
    assert dets
    for d in dets:
        e = d.evidence
        assert e and e.claim and e.supporting and e.check and e.provenance
        assert 0.0 <= d.confidence <= 1.0
        assert d.recommended_action


def test_engine_is_deterministic():
    g1, cfg1, inj1, e1, pi1 = _run()
    g2, cfg2, inj2, e2, pi2 = _run()
    sig1 = [(t, d.entity_id, d.detected, d.shape.value) for t in pi1 for d in pi1[t]]
    sig2 = [(t, d.entity_id, d.detected, d.shape.value) for t in pi2 for d in pi2[t]]
    assert sig1 == sig2


def test_all_three_use_cases_detected_in_one_run():
    g, cfg, inj, eng, pi = _run()
    detected_layers = {(d.entity_id, d.layer) for t in pi for d in pi[t] if d.detected}
    gt = {(x.true_entity, x.true_layer) for x in inj.real_faults()}
    # every ground-truth (entity, layer) was detected at some interval
    for pair in gt:
        assert pair in detected_layers, f"ground-truth fault {pair} never detected"


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
    print(f"\nModule 4 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
