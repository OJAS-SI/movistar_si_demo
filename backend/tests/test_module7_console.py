"""
Standalone test for Module 7 - Visual narrative and operator console.

    python tests/test_module7_console.py     (no dependencies)
    pytest tests/test_module7_console.py

Acceptance criteria (from the roadmap): the console model is faithful to the run (the
right shape per use case, the four beats present and ordered, the recommendation and
receipt and score, the abstention and the rejected decoys), the renderers produce a
manager-readable text console and a self-contained HTML console, and the renderers
read only from the verdicts (they never touch the raw four-field stream).
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
from si_core.diagnosis import DiagnosisFormatter, DiagnosisReport, ReceiptCard
from si_core.scoring import ScoringHarness, ScoreReport
from si_core.console import ConsoleBuilder, ConsoleModel, render_html, render_text


def _model(cfg=None):
    cfg = cfg or c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    fmt = DiagnosisFormatter(g)
    harn = ScoringHarness(cfg)
    return g, cfg, ConsoleBuilder(g).from_pipeline(inj, eng, fmt, harn)


# ---------------------------------------------------------------------------
# 1. The model is faithful to the run
# ---------------------------------------------------------------------------

def test_three_panels_with_correct_shapes():
    g, cfg, model = _model()
    assert len(model.fault_panels) == 3
    by_uc = {p.use_case: p for p in model.fault_panels}
    assert by_uc[c.UseCase.UC1_NETWORK_NODE].shape == c.Shape.CLUSTER
    assert by_uc[c.UseCase.UC2_INDIVIDUAL].shape == c.Shape.SINGLE
    assert by_uc[c.UseCase.UC3_INVISIBLE].shape == c.Shape.CLUSTER


def test_four_beats_present_and_ordered():
    g, cfg, model = _model()
    for p in model.fault_panels:
        assert [b.name for b in p.beats] == ["Stream", "Form", "Predict", "Prescribe"]


def test_predict_beat_shows_the_forming_shape_widening():
    g, cfg, model = _model()
    for p in model.fault_panels:
        predict = next(b for b in p.beats if b.name == "Predict")
        assert "widen" in predict.text.lower()


def test_each_panel_has_report_and_score():
    g, cfg, model = _model()
    for p in model.fault_panels:
        assert p.report.headline and p.report.receipt is not None
        assert p.score.n_detected == 1
        assert p.score.localization_accuracy == 1.0


def test_honest_panel_shows_abstention_and_clean_decoys():
    g, cfg, model = _model()
    h = model.honest
    assert h.abstention is not None and "Competence boundary" in h.abstention.headline
    assert h.n_decoys_fired == 0 and h.n_decoys >= 3
    assert h.false_positive_rate == 0.0


# ---------------------------------------------------------------------------
# 2. The text renderer
# ---------------------------------------------------------------------------

def test_text_render_contains_the_narrative_and_scorecard():
    g, cfg, model = _model()
    text = render_text(model)
    assert "MOVISTAR SERVICE INTELLIGENCE" in text
    for beat in ["Stream", "Form", "Predict", "Prescribe"]:
        assert beat in text
    assert "Certified-decision receipt" in text
    assert "HONEST INSTRUMENTS" in text and "Competence boundary" in text
    assert "SCORECARD" in text and "false-positive rate" in text


# ---------------------------------------------------------------------------
# 3. The HTML renderer is self-contained and faithful
# ---------------------------------------------------------------------------

def test_html_is_self_contained():
    g, cfg, model = _model()
    h = render_html(model)
    assert h.startswith("<!doctype html>")
    assert '<div class="app">' in h            # the interactive twin shell
    # self-contained: every asset (script, style, svg, data) is inline; nothing
    # is fetched from the network.
    low = h.lower()
    assert 'src="http' not in low and "src='http" not in low
    assert 'href="http' not in low and "href='http" not in low
    assert "<link" not in low


def test_html_is_the_interactive_twin_reflecting_the_real_run():
    g, cfg, model = _model()
    h = render_html(model)
    # the three-tab operator shell is present
    assert "Analyst" in h and "Management" in h and "Map of Spain" in h
    assert "<svg" in h and "viewBox" in h
    # the overlay injects THIS run's real element ids, one per detected fault
    for p in model.fault_panels:
        assert p.report.diagnosis.entity_id in h
    # and the real headlines the pipeline produced
    for p in model.fault_panels:
        assert p.report.headline in h


def test_html_contains_receipts_scorecard_and_honesty():
    g, cfg, model = _model()
    h = render_html(model)
    low = h.lower()
    assert "certified-decision receipt" in low
    assert "scorecard" in low and "false-positive rate" in low
    assert "decoys" in low


# ---------------------------------------------------------------------------
# 4. The renderers read only from the verdicts (no raw stream needed)
# ---------------------------------------------------------------------------

def test_renderers_need_only_verdicts_not_the_stream():
    # Build a model from hand-made reports and a hand-made scorecard, with NO injector
    # and NO telemetry, and confirm both renderers work. This proves the console proper
    # never touches the four-field stream.
    cfg = c.tiny_config()
    g = build_service_graph(cfg)

    def mk_report(entity, layer, shape, headline):
        prov = c.Provenance(0, 5, (entity,), "n")
        ev = c.Evidence("a claim", ("s1", "s2"), "a check", prov)
        traj = c.PredictedTrajectory(rising=True, horizon_interval=14, detail="widening")
        diag = c.Diagnosis(5, True, False, entity, layer, shape, 0.95, traj, ev, "do the thing")
        rc = ReceiptCard("a claim", ["e1", "e2"], "a check", "a provenance line", 0.95)
        return DiagnosisReport(5, "detection", headline, "degraded", rc, diag)

    olt = g.olt_ids[0]
    score = c.Score(use_case=c.UseCase.UC1_NETWORK_NODE, n_faults=1, n_detected=1,
                    mean_lead_time_intervals=2.0, localization_accuracy=1.0,
                    layer_attribution_accuracy=1.0, box_swap_discrimination=None,
                    false_positive_rate=0.0, action_correctness=1.0, note="ok")
    sr = ScoreReport(per_use_case=[score], false_positive_rate=0.0, n_non_fault_intervals=10,
                     n_spurious_intervals=0, n_decoys=3, n_decoys_fired=0, interval_seconds=300)
    rep = mk_report(olt, c.Layer.ACCESS, c.Shape.CLUSTER, "Access node degrading: 5 homes")
    model = ConsoleBuilder(g).build([(score, rep)], sr, abstention=None)

    text = render_text(model)
    html = render_html(model)
    assert "Access node degrading" in text and "Access node degrading" in html
    assert html.startswith("<!doctype html>")


# ---------------------------------------------------------------------------
# 5. Determinism
# ---------------------------------------------------------------------------

def test_console_is_deterministic():
    _, _, m1 = _model()
    _, _, m2 = _model()
    assert render_text(m1) == render_text(m2)
    assert render_html(m1) == render_html(m2)


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
    print(f"\nModule 7 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
