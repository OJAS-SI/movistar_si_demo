"""
Growing integration test for the Movistar SI demo.

The roadmap calls for an integration test that grows as each module joins, running
the assembled pipeline so far. At Module 0 there is no pipeline yet, so this test
confirms the foundation itself integrates: the public contracts import cleanly from
a fresh process and compose into a coherent, pipeline-shaped usage end to end.

As later modules land, sections are appended here:
  Module 1 -> topology builds and is well-formed
  Module 2 -> telemetry streams two joined channels
  Module 3 -> faults inject with ground truth
  Module 4 -> SI engine localizes on the core stream
  ...        through to the full one-command run under Module 8.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import si_core.contracts as c


def test_public_surface_is_complete():
    """Every symbol the foundation promises is importable from the one surface."""
    for name in c.__all__:
        assert hasattr(c, name), f"missing public symbol: {name}"


def test_contracts_compose_into_a_mini_pipeline():
    """Walk the contracts in the shape the real pipeline will use them, proving they
    fit together: a core observation and its enrichment, joined; a diagnosis with a
    receipt; ground truth; and a score. This is the foundation working as a whole."""
    cfg = c.tiny_config()
    rng = c.SeededRandom(cfg.seed).child("integration")

    # An OLT emits a magnitude this interval (the four-field core record only).
    core = c.make_core_record(entity_src="OLT-2807001-03", entity_dst="AGG-28-01",
                              timestamp=120, magnitude=4.2 + rng.random())

    # Its enrichment travels on the separate channel, joined by (entity_id, time).
    enr = c.EnrichmentRecord(entity_id="OLT-2807001-03", timestamp=120,
                             entity_type=c.EntityType.OLT, layer=c.Layer.ACCESS,
                             fields={"optical_rx_power": -18.4, "olt_model": "MA5600T"})
    assert core.join_key == enr.join_key  # the only bridge between the channels

    # The SI engine (later, Module 4) would consume the core stream through the
    # boundary guard; confirm a clean core stream passes the guard here.
    clean = list(c.assert_core_stream_clean([core]))
    assert clean == [core]

    # A diagnosis with its certified-decision receipt, in the external register.
    prov = c.Provenance(interval_start=95, interval_end=120,
                        entities_examined=("OLT-2807001-03",),
                        note="25-interval window on the access cluster")
    ev = c.Evidence(
        claim="Access node OLT-2807001-03 degrading: rising freeze/re-tune across its homes",
        supporting=("18 homes with rising magnitude over 25 min", "shared parent OLT-2807001-03"),
        check="pattern is a cluster on one node, inconsistent with a single-home or content fault",
        provenance=prov)
    diag = c.Diagnosis(timestamp=120, detected=True, abstained=False,
                       entity_id="OLT-2807001-03", layer=c.Layer.ACCESS,
                       shape=c.Shape.CLUSTER, confidence=0.86,
                       trajectory=c.PredictedTrajectory(rising=True, horizon_interval=132,
                                                        detail="cluster projected to widen"),
                       evidence=ev,
                       recommended_action="inspect aggregation port before complaints escalate")
    # The diagnosed layer matches the canonical layer the shape implies.
    assert c.SHAPE_TO_LAYER[diag.shape] == diag.layer == c.Layer.ACCESS

    # Ground truth for the same injected fault (Module 3 would record this).
    gt = c.GroundTruthLabel(
        fault_id="F-UC1-001", use_case=c.UseCase.UC1_NETWORK_NODE, onset_time=110,
        affected_entities=("HH-2807001-01", "HH-2807001-02"),
        true_entity="OLT-2807001-03", true_layer=c.Layer.ACCESS,
        ramp=c.RampProfile.GRADUAL, magnitude=4.0,
        recommended_action="inspect aggregation port before complaints escalate")

    # The scoring harness (Module 6) would compare diagnosis to ground truth.
    located_correctly = diag.entity_id == gt.true_entity
    layer_correct = diag.layer == gt.true_layer
    action_correct = diag.recommended_action == gt.recommended_action
    lead_time = gt.onset_time and (diag.timestamp - gt.onset_time)
    score = c.Score(use_case=c.UseCase.UC1_NETWORK_NODE, n_faults=1,
                    n_detected=1, mean_lead_time_intervals=float(lead_time),
                    localization_accuracy=1.0 if located_correctly else 0.0,
                    layer_attribution_accuracy=1.0 if layer_correct else 0.0,
                    box_swap_discrimination=None, false_positive_rate=0.0,
                    action_correctness=1.0 if action_correct else 0.0)
    assert score.localization_accuracy == 1.0
    assert score.layer_attribution_accuracy == 1.0
    assert score.action_correctness == 1.0


def test_determinism_fingerprint():
    """A whole-foundation determinism check: the same seed yields the same derived
    values across the named child streams a real run will use."""
    def fingerprint(seed):
        m = c.SeededRandom(seed)
        out = []
        for stream in ("topology", "telemetry", "faults", "scoring"):
            ch = m.child(stream)
            out.append((stream, [round(ch.random(), 6) for _ in range(5)]))
        return out
    assert fingerprint(20260629) == fingerprint(20260629)



# ---------------------------------------------------------------------------
# Module 1 - topology integrates with the foundation
# ---------------------------------------------------------------------------

def test_module1_topology_builds_and_integrates():
    """The topology generator builds a well-formed, Spain-grounded graph on top of
    the Module 0 contracts, and yields the shared-structure index the SI engine and
    scorer will consume."""
    from si_core.topology import build_service_graph

    g = build_service_graph(c.tiny_config())

    # The graph uses the foundation's enumerations directly.
    for n in g.nodes.values():
        assert isinstance(n.entity_type, c.EntityType)
        assert isinstance(n.layer, c.Layer)

    # Every home traces a complete path; the membership index is usable.
    assert len(g.stb_ids) > 0
    a_home = g.stb_ids[0]
    m = g.stb_membership[a_home]
    assert m.olt_id in g.nodes and m.content_id in g.nodes

    # The three shared-structure groupings the SI engine reads are present and cover
    # every home (so cluster / path / source faults are all expressible).
    assert sum(len(v) for v in g.stbs_by_olt.values()) == len(g.stb_ids)
    assert sum(len(v) for v in g.stbs_by_content.values()) == len(g.stb_ids)

    # A downstream diagnosis about an access node composes cleanly with Module 0:
    # the OLT's layer is ACCESS, matching the CLUSTER shape the engine would assign.
    some_olt = g.olt_ids[0]
    assert g.nodes[some_olt].layer == c.Layer.ACCESS
    assert c.SHAPE_TO_LAYER[c.Shape.CLUSTER] == g.nodes[some_olt].layer


def test_module1_is_deterministic_with_foundation_seed():
    """The graph is a deterministic function of the DemoConfig seed, like everything
    built on the foundation."""
    from si_core.topology import build_service_graph
    a = build_service_graph(c.tiny_config())
    b = build_service_graph(c.tiny_config())
    assert a.stb_ids == b.stb_ids
    assert [a.stb_membership[s].path() for s in a.stb_ids] == \
           [b.stb_membership[s].path() for s in b.stb_ids]



# ---------------------------------------------------------------------------
# Module 2 - topology + telemetry produce clean, joined, healthy streams
# ---------------------------------------------------------------------------

def test_module2_telemetry_integrates_with_topology():
    """The telemetry generator runs over the Module 1 graph and produces two streams
    that join cleanly: a strictly four-field core stream the SI engine can consume,
    and enrichment joined by (entity_id, timestamp)."""
    from si_core.topology import build_service_graph
    from si_core.telemetry import TelemetryGenerator

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    gen = TelemetryGenerator(g, cfg)

    it = gen.interval(12)
    # the core stream passes the four-field boundary guard
    clean = list(c.assert_core_stream_clean(it.core))
    assert len(clean) == len(it.core) == 3 * len(g.stb_ids)
    # every emitting entity joins to an enrichment record at this interval
    for r in it.core:
        assert r.entity_src in it.enrichment
        assert it.enrichment[r.entity_src].join_key == (r.entity_src, it.timestamp)


def test_module2_healthy_world_raises_nothing_precursor():
    """On a healthy network the whole run stays below the healthy ceiling - the
    precursor to the SI engine (Module 4) raising no fault on healthy telemetry."""
    from si_core.topology import build_service_graph
    from si_core.telemetry import TelemetryGenerator

    cfg = c.tiny_config()
    gen = TelemetryGenerator(build_service_graph(cfg), cfg)
    worst = max(r.magnitude for it in gen.stream() for r in it.core)
    assert worst < gen.HEALTHY_CEILING



# ---------------------------------------------------------------------------
# Module 3 - the pipeline injects faults with ground truth
# ---------------------------------------------------------------------------

def test_module3_faults_inject_with_ground_truth():
    """Topology + telemetry + fault injection: the three use-case faults appear in
    the faulted stream above the healthy baseline, the answer key is available, and
    the faulted core stream is still strictly four fields."""
    from si_core.topology import build_service_graph
    from si_core.telemetry import TelemetryGenerator, ACCESS
    from si_core.fault_injection import FaultInjector

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    healthy = TelemetryGenerator(g, cfg)

    # ground truth by construction: three real faults, decoys labelled benign
    assert len(inj.real_faults()) == 3
    assert all(d.is_decoy for d in inj.decoys())

    # the UC1 cluster is elevated above the healthy world at its peak
    uc1 = next(s for s in inj.schedule if s.fault_id == "F-UC1-OLT")
    peak_t = uc1.end - 1
    f_it = inj.interval(peak_t)
    h_it = healthy.interval(peak_t)

    def mag(it, src, dst):
        i = it.core_index.get((src, dst), -1)
        return it.core[i].magnitude if i >= 0 else None

    home = uc1.affected_homes[0]
    assert mag(f_it, home, uc1.target_entity) > mag(h_it, home, uc1.target_entity)

    # the faulted core stream still passes the four-field boundary guard
    assert len(list(c.assert_core_stream_clean(f_it.core))) == len(f_it.core)


def test_module3_healthy_stretch_equals_healthy_world():
    """In a healthy stretch (no active event) the faulted stream is identical to the
    healthy stream, so the engine has clean ground for measuring false positives."""
    from si_core.topology import build_service_graph
    from si_core.telemetry import TelemetryGenerator
    from si_core.fault_injection import FaultInjector

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    healthy = TelemetryGenerator(g, cfg)

    active = set()
    for s in inj.schedule:
        active.update(range(s.onset, s.end))
    quiet = next(t for t in range(cfg.run_intervals) if t not in active)
    f = {(r.entity_src, r.entity_dst): r.magnitude for r in inj.interval(quiet).core}
    h = {(r.entity_src, r.entity_dst): r.magnitude for r in healthy.interval(quiet).core}
    assert f == h



# ---------------------------------------------------------------------------
# Module 4 - the SI engine localizes the injected faults on the four-field stream
# ---------------------------------------------------------------------------

def test_module4_engine_detects_all_three_use_cases():
    """End to end through the engine: on the faulted four-field stream the engine
    detects each of the three injected faults and attributes each to its true layer,
    scored against ground truth, while firing on no healthy interval."""
    from si_core.topology import build_service_graph
    from si_core.fault_injection import FaultInjector
    from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)

    detected = set()
    active = set()
    for s in inj.schedule:
        active.update(range(s.onset, s.end))
    healthy_fire = 0
    for t in range(cfg.run_intervals):
        for d in eng.observe_and_diagnose(t, inj.interval(t).core):
            if d.detected:
                detected.add((d.entity_id, d.layer))
                if t not in active:
                    healthy_fire += 1

    gt = {(x.true_entity, x.true_layer) for x in inj.real_faults()}
    for pair in gt:
        assert pair in detected, f"ground-truth fault {pair} not detected by the engine"
    assert healthy_fire == 0, "engine fired on a healthy interval"


def test_module4_engine_consumes_only_four_fields():
    """The engine is wired to the core stream only; enrichment never reaches it."""
    from si_core.topology import build_service_graph
    from si_core.fault_injection import FaultInjector
    from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    it = inj.interval(10)
    # feeding the faulted core stream works; feeding enrichment is rejected
    eng.observe_and_diagnose(10, it.core)
    try:
        eng.observe_and_diagnose(11, list(it.enrichment.values()))
        raise AssertionError("engine accepted enrichment")
    except TypeError:
        pass



# ---------------------------------------------------------------------------
# Module 5 - the engine's verdict becomes an operator line and a receipt
# ---------------------------------------------------------------------------

def test_module5_diagnosis_formats_each_use_case():
    """The engine's structural verdict flows into the formatter, which joins
    enrichment by (entity_id, timestamp) and produces an operator line and a complete
    certified-decision receipt for each of the three faults."""
    from si_core.topology import build_service_graph
    from si_core.fault_injection import FaultInjector
    from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
    from si_core.diagnosis import DiagnosisFormatter

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    fmt = DiagnosisFormatter(g)

    headlines = {}
    for t in range(cfg.run_intervals):
        it = inj.interval(t)
        for d in eng.observe_and_diagnose(t, it.core):
            if d.detected and d.entity_id not in headlines:
                rep = fmt.format(d, it)
                # every detection produces a full receipt and a placed headline
                assert rep.receipt and rep.receipt.claim and rep.receipt.check
                assert rep.receipt.provenance and rep.receipt.evidence_lines
                headlines[d.entity_id] = (d.shape, rep.headline)

    # the three ground-truth entities each produced a line
    gt_entities = {x.true_entity for x in inj.real_faults()}
    assert gt_entities <= set(headlines.keys())


def test_module5_abstention_defers_to_human():
    """An engine abstention becomes a human-readable deferral, not a guess."""
    from si_core.topology import build_service_graph
    from si_core.fault_injection import FaultInjector
    from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
    from si_core.diagnosis import DiagnosisFormatter

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    fmt = DiagnosisFormatter(g)
    saw = False
    for t in range(cfg.run_intervals):
        it = inj.interval(t)
        for d in eng.observe_and_diagnose(t, it.core):
            if d.abstained:
                rep = fmt.format(d, it)
                assert rep.kind == "abstention" and "Competence boundary" in rep.headline
                saw = True
    assert saw



# ---------------------------------------------------------------------------
# Module 6 - the assembled pipeline scores against ground truth
# ---------------------------------------------------------------------------

def test_module6_scores_the_full_pipeline_against_ground_truth():
    """End to end: topology, telemetry, fault injection, engine, scoring. The harness
    detects all three faults, localizes and attributes each correctly, passes box-swap
    discrimination for the invisible fault, and reports zero false positives."""
    from si_core.topology import build_service_graph
    from si_core.fault_injection import FaultInjector
    from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
    from si_core.scoring import ScoringHarness

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    report = ScoringHarness(cfg).evaluate(inj, eng)

    assert all(s.n_detected == 1 for s in report.per_use_case)
    assert all(s.localization_accuracy == 1.0 for s in report.per_use_case)
    assert all(s.layer_attribution_accuracy == 1.0 for s in report.per_use_case)
    uc3 = next(s for s in report.per_use_case if s.use_case == c.UseCase.UC3_INVISIBLE)
    assert uc3.box_swap_discrimination == 1.0
    assert report.false_positive_rate == 0.0
    assert report.n_decoys_fired == 0


def test_module6_scorecard_renders():
    """The scorecard renders to a manager-readable block with the promised numbers."""
    from si_core.topology import build_service_graph
    from si_core.fault_injection import FaultInjector
    from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
    from si_core.scoring import ScoringHarness

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    text = ScoringHarness(cfg).evaluate(inj, eng).render()
    assert "scorecard" in text and "false-positive rate" in text



# ---------------------------------------------------------------------------
# Module 7 - the console renders the whole story from the verdicts
# ---------------------------------------------------------------------------

def test_module7_console_renders_the_full_demo():
    """End to end: the pipeline's verdicts become a faithful console. Three panels
    with the right shapes, the four beats, the receipts and scores, the abstention and
    the clean decoys, and a self-contained HTML render, all from the verdicts alone."""
    from si_core.topology import build_service_graph
    from si_core.fault_injection import FaultInjector
    from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
    from si_core.diagnosis import DiagnosisFormatter
    from si_core.scoring import ScoringHarness
    from si_core.console import ConsoleBuilder, render_html, render_text

    cfg = c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    model = ConsoleBuilder(g).from_pipeline(inj, eng, DiagnosisFormatter(g), ScoringHarness(cfg))

    assert len(model.fault_panels) == 3
    assert model.honest.abstention is not None
    assert model.honest.n_decoys_fired == 0

    text = render_text(model)
    html = render_html(model)
    assert "Certified-decision receipt" in text
    assert html.startswith("<!doctype html>") and "<svg" in html
    # the console proper carries no four-field records
    assert "entity_src" not in html



# ---------------------------------------------------------------------------
# Module 8 - the orchestrator runs the whole demo from one call
# ---------------------------------------------------------------------------

def test_module8_one_call_runs_and_passes_the_self_test():
    """The capstone: a single orchestrated call wires the whole pipeline in data-flow
    order, runs it deterministically, produces the console, and passes its own
    self-test (all faults detected and attributed, the box swap avoided, no false
    positives)."""
    from si_core.orchestrator import run_demo

    r = run_demo(c.tiny_config())
    assert r.passed()
    assert len(r.console_model.fault_panels) == 3
    assert r.text_console and r.html_console.startswith("<!doctype html>")
    # deterministic from the seed
    r2 = run_demo(c.tiny_config())
    assert r.text_console == r2.text_console


def test_module8_robust_across_seeds():
    """The full pipeline holds up on several random topologies, not just the default."""
    from si_core.orchestrator import run_demo
    for seed in [11, 22, 33]:
        assert run_demo(c.tiny_config(seed=seed)).passed(), f"failed for seed {seed}"


def _run_all():
    import traceback
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t(); passed += 1; print(f"  PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {t.__name__}: {exc}")
            print(traceback.format_exc())
    print(f"\nIntegration test (through Module 8, COMPLETE): {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
