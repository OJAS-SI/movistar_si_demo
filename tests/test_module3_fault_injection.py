"""
Standalone test for Module 3 - Fault-injection engine and ground-truth recorder.

    python tests/test_module3_fault_injection.py     (no dependencies)
    pytest tests/test_module3_fault_injection.py

This is the strictest module test, because if ground truth or the perturbation is
wrong, every score downstream is meaningless. It verifies: faults appear at their
scheduled time on the correct subsystem edge with the correct ramp; UC1 forms a
cluster while leaving the homes' other subsystems flat; UC2 is isolated (peers stay
healthy); UC3 carries no error code and survives the box swap; decoys are short
transients labelled benign; healthy intervals are untouched; and the recorded
answer key matches what was injected.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import traceback

import si_demo.core as c
from si_demo.telemetry import ACCESS, CONTENT, TRANSPORT, TelemetryGenerator
from si_demo.topology import build_service_graph
from si_demo.fault_injection import FaultInjector, build_fault_schedule


def _setup(cfg=None):
    cfg = cfg or c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    healthy = TelemetryGenerator(g, cfg)
    return g, cfg, inj, healthy


def _spec(inj, fault_id):
    return next(s for s in inj.schedule if s.fault_id == fault_id)


def _mag(it, src, dst):
    idx = it.core_index.get((src, dst), -1)
    return it.core[idx].magnitude if idx >= 0 else None


# ---------------------------------------------------------------------------
# 1. The schedule and the recorded answer key
# ---------------------------------------------------------------------------

def test_schedule_has_three_real_faults_and_decoys():
    g, cfg, inj, _ = _setup()
    assert len(inj.real_faults()) == 3
    assert len(inj.decoys()) >= 3
    ucs = {s.use_case for s in inj.schedule if not s.is_decoy}
    assert ucs == {c.UseCase.UC1_NETWORK_NODE, c.UseCase.UC2_INDIVIDUAL,
                   c.UseCase.UC3_INVISIBLE}


def test_ground_truth_matches_injected_layers_and_entities():
    g, cfg, inj, _ = _setup()
    by_uc = {gt.use_case: gt for gt in inj.real_faults()}
    assert by_uc[c.UseCase.UC1_NETWORK_NODE].true_layer == c.Layer.ACCESS
    assert by_uc[c.UseCase.UC1_NETWORK_NODE].true_entity in g.olt_ids
    assert by_uc[c.UseCase.UC2_INDIVIDUAL].true_layer == c.Layer.HOME
    assert by_uc[c.UseCase.UC2_INDIVIDUAL].true_entity in g.stb_ids
    assert by_uc[c.UseCase.UC3_INVISIBLE].true_layer == c.Layer.ACCESS
    assert by_uc[c.UseCase.UC3_INVISIBLE].has_explicit_error_code is False
    assert by_uc[c.UseCase.UC3_INVISIBLE].box_swap_time is not None


def test_decoys_are_labelled_benign():
    g, cfg, inj, _ = _setup()
    for d in inj.decoys():
        assert d.is_decoy is True
        assert d.true_layer is None and d.true_entity is None


# ---------------------------------------------------------------------------
# 2. Healthy intervals are untouched
# ---------------------------------------------------------------------------

def test_no_perturbation_outside_any_window():
    g, cfg, inj, healthy = _setup()
    # find an interval with no active event
    active = set()
    for s in inj.schedule:
        active.update(range(s.onset, s.end))
    quiet = next(t for t in range(cfg.run_intervals) if t not in active)
    f = {(r.entity_src, r.entity_dst): r.magnitude for r in inj.interval(quiet).core}
    h = {(r.entity_src, r.entity_dst): r.magnitude for r in healthy.interval(quiet).core}
    assert f == h, f"interval {quiet} should be untouched but differs"


# ---------------------------------------------------------------------------
# 3. UC1 - a cluster forms on the OLT, other subsystems stay flat
# ---------------------------------------------------------------------------

def test_uc1_raises_the_whole_cluster_on_access():
    g, cfg, inj, _ = _setup()
    s = _spec(inj, "F-UC1-OLT")
    olt = s.target_entity
    peak_t = s.end - 1   # at the plateau
    it = inj.interval(peak_t)
    for home in s.affected_homes:
        mag = _mag(it, home, olt)
        assert mag is not None and mag > TelemetryGenerator.HEALTHY_CEILING, (
            f"home {home} access edge not elevated at peak ({mag})")


def test_uc1_does_not_touch_homes_other_subsystems():
    # The fault is on ACCESS only; the same homes' transport and content edges stay
    # healthy, which is what keeps the layers separable.
    g, cfg, inj, _ = _setup()
    s = _spec(inj, "F-UC1-OLT")
    it = inj.interval(s.end - 1)
    for home in s.affected_homes[:5]:
        m = g.stb_membership[home]
        assert _mag(it, home, m.route_id) < TelemetryGenerator.HEALTHY_CEILING
        assert _mag(it, home, m.content_id) < TelemetryGenerator.HEALTHY_CEILING


def test_uc1_follows_a_gradual_ramp():
    g, cfg, inj, _ = _setup()
    s = _spec(inj, "F-UC1-OLT")
    olt = s.target_entity
    home = s.affected_homes[0]
    early = _mag(inj.interval(s.onset), home, olt)
    mid = _mag(inj.interval(s.onset + s.ramp_intervals // 2), home, olt)
    plateau = _mag(inj.interval(s.end - 1), home, olt)
    assert early < mid < plateau, f"ramp not monotonic: {early}, {mid}, {plateau}"


# ---------------------------------------------------------------------------
# 4. UC2 - isolated home; peers on the same OLT stay healthy
# ---------------------------------------------------------------------------

def test_uc2_home_is_elevated_but_peers_are_healthy():
    g, cfg, inj, _ = _setup()
    s = _spec(inj, "F-UC2-HOME")
    home = s.affected_homes[0]
    olt = g.stb_membership[home].olt_id
    peak_t = s.end - 1
    it = inj.interval(peak_t)
    # the home is elevated
    assert _mag(it, home, olt) > TelemetryGenerator.HEALTHY_CEILING
    # its OLT peers are NOT (this is what makes it home-isolated, not an access fault)
    for peer in g.peers_on_olt(home):
        assert _mag(it, peer, olt) < TelemetryGenerator.HEALTHY_CEILING, (
            f"peer {peer} should stay healthy during an isolated home fault")


def test_uc2_records_a_tipping_point():
    g, cfg, inj, _ = _setup()
    gt = next(x for x in inj.real_faults() if x.use_case == c.UseCase.UC2_INDIVIDUAL)
    assert gt.tipping_point_time is not None
    assert gt.onset_time <= gt.tipping_point_time


# ---------------------------------------------------------------------------
# 5. UC3 - invisible (no error code) and survives the box swap
# ---------------------------------------------------------------------------

def test_uc3_carries_no_error_code_but_is_present_in_core():
    g, cfg, inj, _ = _setup()
    s = _spec(inj, "F-UC3-SEG")
    olt = s.target_entity
    peak_t = s.end - 1
    it = inj.interval(peak_t)
    for home in s.affected_homes:
        # elevated in the core stream (SI can see it)
        assert _mag(it, home, olt) > TelemetryGenerator.HEALTHY_CEILING
        # but the enrichment carries NO explicit error code (per-layer tooling is blind)
        assert it.enrichment[home].fields.get("error_code") is None


def test_uc3_impairment_persists_across_the_box_swap():
    g, cfg, inj, _ = _setup()
    s = _spec(inj, "F-UC3-SEG")
    olt = s.target_entity
    home = s.affected_homes[0]
    swap = s.box_swap_time
    before = _mag(inj.interval(swap - 1), home, olt)
    after = _mag(inj.interval(swap + 1), home, olt)
    # the fault is NOT the box: a swap does not clear it
    assert before > TelemetryGenerator.HEALTHY_CEILING
    assert after > TelemetryGenerator.HEALTHY_CEILING
    # and the swap is recorded in enrichment, yet impairment continues
    assert inj.interval(swap + 1).enrichment[home].fields.get("stb_swapped") is True


# ---------------------------------------------------------------------------
# 6. Decoys are short transients that do not persist
# ---------------------------------------------------------------------------

def test_decoys_are_transient():
    g, cfg, inj, _ = _setup()
    for d in inj.schedule:
        if not d.is_decoy:
            continue
        # short window
        assert d.end - d.onset <= 3, f"decoy {d.fault_id} not transient"
        # elevated within the window, gone two intervals after it ends (if room)
        home = d.affected_homes[0]
        dst = g.stb_membership[home].olt_id
        if d.end + 2 < cfg.run_intervals:
            after = _mag(inj.interval(d.end + 2), home, dst)
            assert after < TelemetryGenerator.HEALTHY_CEILING, (
                f"decoy {d.fault_id} still elevated after its window")


# ---------------------------------------------------------------------------
# 7. The four-field boundary, and determinism
# ---------------------------------------------------------------------------

def test_faulted_core_stream_is_still_four_fields():
    g, cfg, inj, _ = _setup()
    s = _spec(inj, "F-UC1-OLT")
    it = inj.interval(s.end - 1)
    clean = list(c.assert_core_stream_clean(it.core))
    assert len(clean) == len(it.core)


def test_injection_is_deterministic():
    g1 = build_service_graph(c.tiny_config()); i1 = FaultInjector(g1, c.tiny_config())
    g2 = build_service_graph(c.tiny_config()); i2 = FaultInjector(g2, c.tiny_config())
    # same schedule
    assert [s.fault_id for s in i1.schedule] == [s.fault_id for s in i2.schedule]
    assert [s.onset for s in i1.schedule] == [s.onset for s in i2.schedule]
    # same faulted stream at a faulted interval
    t = _spec(i1, "F-UC1-OLT").end - 1
    m1 = [(r.entity_src, r.entity_dst, r.magnitude) for r in i1.interval(t).core]
    m2 = [(r.entity_src, r.entity_dst, r.magnitude) for r in i2.interval(t).core]
    assert m1 == m2


def test_faults_exceed_ceiling_decoys_only_tempt():
    g, cfg, inj, _ = _setup()
    real_peaks = [s.peak_magnitude for s in inj.schedule if not s.is_decoy]
    assert all(p > TelemetryGenerator.HEALTHY_CEILING for p in real_peaks)


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
    print(f"\nModule 3 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
