"""
Standalone test for Module 5 - Diagnosis and certified-receipt formatter.

    python tests/test_module5_diagnosis.py     (no dependencies)
    pytest tests/test_module5_diagnosis.py

Acceptance criteria (from the roadmap): given a known engine verdict and the matching
enrichment, the formatter produces the correct operator line and a receipt with every
leg present; the headline count matches the signature; an abstention renders as a
deferral to a human; all-clear renders cleanly; and the artifact stays strictly in the
external register (no operator-algebra vocabulary leaks into a client-facing line).
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import re
import traceback

import si_core.contracts as c
from si_core.topology import build_service_graph
from si_core.fault_injection import FaultInjector
from si_core.si_engine import NetworkMap, StructuralIntelligenceEngine
from si_core.diagnosis import DiagnosisFormatter, DiagnosisReport, ReceiptCard


# Internal-register vocabulary that must NEVER appear in a client-facing artifact.
_FORBIDDEN = [
    "spectral", "koopman", "wasserstein", "lyapunov", "hamiltonian", "sheaf",
    "meijer", "cohomolog", "laplacian", "dirichlet", "holonomy", "conformal",
    "master identity", "twelve-tuple", "optimal transport", "persistence diagram",
    "value-weighted", "asset graph", "knowledge bank", "kb1", "operator algebra",
    "noether", "symplectic",
]


def _collect(cfg=None):
    """Run the pipeline and collect, for each first detection and one abstention and
    one all-clear, the (report) produced by the formatter."""
    cfg = cfg or c.tiny_config()
    g = build_service_graph(cfg)
    inj = FaultInjector(g, cfg)
    eng = StructuralIntelligenceEngine(NetworkMap(g), cfg)
    fmt = DiagnosisFormatter(g)
    reports = {"detection": {}, "abstention": None, "all_clear": None}
    active = set()
    for s in inj.schedule:
        active.update(range(s.onset, s.end))
    for t in range(cfg.run_intervals):
        it = inj.interval(t)
        ds = eng.observe_and_diagnose(t, it.core)
        if not ds and reports["all_clear"] is None and t not in active:
            reports["all_clear"] = fmt.all_clear(t)
        for d in ds:
            rep = fmt.format(d, it)
            if d.detected and d.entity_id not in reports["detection"]:
                reports["detection"][d.entity_id] = rep
            if d.abstained and reports["abstention"] is None:
                reports["abstention"] = rep
    return g, cfg, inj, fmt, reports


def _by_shape(reports, shape):
    for rep in reports["detection"].values():
        if rep.diagnosis.shape == shape:
            return rep
    return None


# ---------------------------------------------------------------------------
# 1. The operator line per use case
# ---------------------------------------------------------------------------

def test_uc1_cluster_line_names_node_place_count_and_action():
    g, cfg, inj, fmt, reports = _collect()
    rep = _by_shape(reports, c.Shape.CLUSTER)
    assert rep is not None
    h = rep.headline
    assert "Access node" in h and rep.diagnosis.entity_id in h
    assert "homes" in h and "Recommended:" in h
    assert "cluster" in h.lower()
    # placed in its region / central office
    assert g.nodes[rep.diagnosis.entity_id].region in h


def test_uc2_single_line_states_isolation_and_no_truck_roll():
    g, cfg, inj, fmt, reports = _collect()
    rep = None
    for r in reports["detection"].values():
        if r.diagnosis.shape == c.Shape.SINGLE:
            rep = r
    assert rep is not None
    h = rep.headline
    assert "Household" in h and "isolation" in h.lower()
    assert "peers" in h.lower() and "healthy" in h.lower()
    assert "no truck roll" in h.lower()


def test_uc3_line_recommends_no_box_swap():
    # UC3 is detected as an access cluster; the action must be network-side, never a
    # box swap. (Both UC3 clusters in the run satisfy this.)
    g, cfg, inj, fmt, reports = _collect()
    clusters = [r for r in reports["detection"].values()
                if r.diagnosis.shape == c.Shape.CLUSTER]
    assert clusters
    for r in clusters:
        assert "box" not in r.headline.lower()


# ---------------------------------------------------------------------------
# 2. The receipt - every leg present, and the enrichment join happened
# ---------------------------------------------------------------------------

def test_every_detection_receipt_has_all_legs():
    g, cfg, inj, fmt, reports = _collect()
    assert reports["detection"]
    for rep in reports["detection"].values():
        r = rep.receipt
        assert isinstance(r, ReceiptCard)
        assert r.claim and r.evidence_lines and r.check and r.provenance
        assert 0.0 <= r.confidence <= 1.0
        # provenance attests the four-field stream
        assert "four-field magnitude stream" in r.provenance


def test_enrichment_was_joined_into_the_receipt():
    # The cluster receipt should carry joined OLT enrichment (port utilization); the
    # single receipt should carry joined home enrichment (Wi-Fi SNR). This proves the
    # join by (entity_id, timestamp) happened.
    g, cfg, inj, fmt, reports = _collect()
    cluster = _by_shape(reports, c.Shape.CLUSTER)
    single = None
    for r in reports["detection"].values():
        if r.diagnosis.shape == c.Shape.SINGLE:
            single = r
    assert cluster and any("port utilization" in e for e in cluster.receipt.evidence_lines)
    assert single and any("Wi-Fi SNR" in e for e in single.receipt.evidence_lines)


def test_headline_count_matches_signature_count():
    g, cfg, inj, fmt, reports = _collect()
    for rep in reports["detection"].values():
        if rep.diagnosis.shape in (c.Shape.CLUSTER, c.Shape.PATH, c.Shape.SOURCE):
            n_sig = len(rep.diagnosis.evidence.provenance.entities_examined)
            m = re.search(r"(\d+) homes", rep.headline)
            assert m and int(m.group(1)) == n_sig, (
                f"headline count {m.group(1) if m else None} != signature {n_sig}")


# ---------------------------------------------------------------------------
# 3. Abstention and all-clear
# ---------------------------------------------------------------------------

def test_abstention_renders_as_a_deferral():
    g, cfg, inj, fmt, reports = _collect()
    rep = reports["abstention"]
    assert rep is not None and rep.kind == "abstention"
    assert "Competence boundary" in rep.headline
    assert rep.diagnosis.entity_id is None
    assert rep.receipt is not None and rep.receipt.claim


def test_all_clear_renders_cleanly():
    g, cfg, inj, fmt, reports = _collect()
    rep = reports["all_clear"]
    assert rep is not None and rep.kind == "all_clear"
    assert "All clear" in rep.headline and rep.health_band == "healthy"
    assert rep.receipt is None


# ---------------------------------------------------------------------------
# 4. Two-register discipline - nothing internal leaks into the artifact
# ---------------------------------------------------------------------------

def test_no_internal_register_terms_leak():
    g, cfg, inj, fmt, reports = _collect()
    blobs = [rep.render() for rep in reports["detection"].values()]
    if reports["abstention"]:
        blobs.append(reports["abstention"].render())
    if reports["all_clear"]:
        blobs.append(reports["all_clear"].render())
    for blob in blobs:
        low = blob.lower()
        for term in _FORBIDDEN:
            assert term not in low, f"internal-register term '{term}' leaked into a client artifact"


def test_render_is_a_nonempty_multiline_block():
    g, cfg, inj, fmt, reports = _collect()
    rep = _by_shape(reports, c.Shape.CLUSTER)
    text = rep.render()
    assert "Structural Health Index:" in text
    assert "Certified-decision receipt:" in text
    assert text.count("\n") >= 5


# ---------------------------------------------------------------------------
# 5. Determinism
# ---------------------------------------------------------------------------

def test_formatting_is_deterministic():
    _, _, _, _, r1 = _collect()
    _, _, _, _, r2 = _collect()
    h1 = sorted(rep.headline for rep in r1["detection"].values())
    h2 = sorted(rep.headline for rep in r2["detection"].values())
    assert h1 == h2


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
    print(f"\nModule 5 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
