"""
Standalone test for Module 2 - Telemetry and baseline generator.

    python tests/test_module2_telemetry.py     (no dependencies)
    pytest tests/test_module2_telemetry.py

Acceptance criteria (from the roadmap): healthy streams are stationary around their
baselines with believable noise; seasonality appears at the right cadence; the two
streams join on their keys; the core stream is strictly four fields; each home emits
its three subsystem edges; with no faults nothing exceeds the healthy ceiling (so the
engine downstream raises nothing); and interval(t) is a deterministic, pure function
of t.
"""

from __future__ import annotations

import os
import statistics
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import traceback

import si_demo.core as c
from si_demo.topology import build_service_graph
from si_demo.telemetry import ACCESS, CONTENT, TRANSPORT, IntervalTelemetry, TelemetryGenerator


def _setup(cfg=None):
    cfg = cfg or c.tiny_config()
    g = build_service_graph(cfg)
    return g, cfg, TelemetryGenerator(g, cfg)


# ---------------------------------------------------------------------------
# 1. Structure of the emitted stream
# ---------------------------------------------------------------------------

def test_each_home_emits_three_subsystem_edges():
    g, cfg, gen = _setup()
    it = gen.interval(3)
    assert len(it.core) == 3 * len(g.stb_ids)
    # for a sample home, exactly one edge to its OLT, its route, its content
    stb = g.stb_ids[0]
    m = g.stb_membership[stb]
    dsts = {r.entity_dst for r in it.core if r.entity_src == stb}
    assert dsts == {m.olt_id, m.route_id, m.content_id}


def test_core_stream_is_strictly_four_fields():
    g, cfg, gen = _setup()
    it = gen.interval(7)
    # passes the SI entry guard: every element is a CoreRecord and nothing more
    clean = list(c.assert_core_stream_clean(it.core))
    assert len(clean) == len(it.core)


def test_streams_join_on_their_keys():
    g, cfg, gen = _setup()
    it = gen.interval(9)
    # every home that emits core records has an enrichment record this interval
    srcs = {r.entity_src for r in it.core}
    for s in srcs:
        assert s in it.enrichment, f"no enrichment to join for {s}"
        assert it.enrichment[s].timestamp == it.timestamp


def test_enrichment_carries_per_layer_flow_fields():
    g, cfg, gen = _setup()
    it = gen.interval(2)
    # a home carries freeze_duration; an OLT carries port_utilization; a route
    # carries transport_load; a content source carries segment_failures
    stb = g.stb_ids[0]
    assert "freeze_duration" in it.enrichment[stb].fields
    assert "port_utilization" in it.enrichment[g.olt_ids[0]].fields
    assert "transport_load" in it.enrichment[g.route_ids[0]].fields
    assert "segment_failures" in it.enrichment[g.content_ids[0]].fields


def test_enrichment_never_enters_core():
    # The four-field boundary: enrichment values must not appear as core magnitudes.
    g, cfg, gen = _setup()
    it = gen.interval(4)
    # core records carry only the four fields; confirm no enrichment key leaked in
    for r in it.core:
        assert set(r.__slots__) == set(c.CORE_RECORD_FIELDS)


# ---------------------------------------------------------------------------
# 2. Healthy behaviour - stationary, bounded, seasonal
# ---------------------------------------------------------------------------

def test_healthy_stream_stays_below_ceiling():
    # With no faults injected, nothing should exceed the healthy ceiling - the
    # precursor to the engine raising nothing on a healthy network.
    g, cfg, gen = _setup()
    worst = 0.0
    for t in range(cfg.run_intervals):
        it = gen.interval(t)
        worst = max(worst, max(r.magnitude for r in it.core))
    assert worst < gen.HEALTHY_CEILING, f"healthy worst {worst} exceeded ceiling"


def test_healthy_stream_is_stationary_around_baseline():
    # A home's access signal over time should hover near its baseline (low mean,
    # modest spread), not drift or spike.
    g, cfg, gen = _setup()
    stb = g.stb_ids[0]
    hb = gen.home_baseline[stb]
    vals = [gen.base_magnitude(stb, ACCESS, t) for t in range(cfg.run_intervals)]
    mean = statistics.mean(vals)
    # mean within a reasonable factor of the (seasonality-lifted) baseline
    assert hb.access_base * 0.6 <= mean <= hb.access_base * 1.8, (mean, hb.access_base)
    assert max(vals) < gen.HEALTHY_CEILING


def test_seasonality_lifts_prime_time():
    # Prime-time intervals should carry a higher population mean than off-peak.
    g, cfg, gen = _setup()
    prime_iod = (cfg.prime_time_start + cfg.prime_time_end) // 2
    offpeak_iod = (cfg.prime_time_start + cfg.prime_time_end) // 2 + cfg.intervals_per_day // 2
    offpeak_iod %= cfg.intervals_per_day

    def pop_mean(iod):
        it = gen.interval(iod)
        return statistics.mean(r.magnitude for r in it.core)

    assert gen.seasonality(prime_iod) > gen.seasonality(offpeak_iod)
    assert pop_mean(prime_iod) > pop_mean(offpeak_iod)


def test_three_subsystems_are_independent():
    # The three per-home signals are drawn independently, so they are not identical.
    g, cfg, gen = _setup()
    stb = g.stb_ids[0]
    a = [gen.base_magnitude(stb, ACCESS, t) for t in range(cfg.run_intervals)]
    tr = [gen.base_magnitude(stb, TRANSPORT, t) for t in range(cfg.run_intervals)]
    co = [gen.base_magnitude(stb, CONTENT, t) for t in range(cfg.run_intervals)]
    assert a != tr and a != co and tr != co


# ---------------------------------------------------------------------------
# 3. Determinism - interval(t) is a pure, reproducible function of t
# ---------------------------------------------------------------------------

def test_interval_is_pure_function_of_t():
    g, cfg, gen = _setup()
    # calling out of order must not change results
    a = gen.interval(10)
    _ = gen.interval(3)
    b = gen.interval(10)
    assert [r.magnitude for r in a.core] == [r.magnitude for r in b.core]


def test_same_config_same_telemetry():
    g1, cfg1, gen1 = _setup()
    g2, cfg2, gen2 = _setup()
    for t in (0, 5, 25):
        m1 = [(r.entity_src, r.entity_dst, r.magnitude) for r in gen1.interval(t).core]
        m2 = [(r.entity_src, r.entity_dst, r.magnitude) for r in gen2.interval(t).core]
        assert m1 == m2


def test_stream_yields_every_interval():
    g, cfg, gen = _setup()
    seen = [it.timestamp for it in gen.stream()]
    assert seen == list(range(cfg.run_intervals))


def test_core_index_locates_records():
    # The core_index must let Module 3 find a specific home/subsystem edge to perturb.
    g, cfg, gen = _setup()
    it = gen.interval(6)
    stb = g.stb_ids[0]
    m = g.stb_membership[stb]
    idx = it.core_record_for(stb, m.olt_id)
    assert idx >= 0
    assert it.core[idx].entity_src == stb and it.core[idx].entity_dst == m.olt_id


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
    print(f"\nModule 2 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
