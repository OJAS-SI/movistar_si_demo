"""
Standalone test for Module 1 - Topology and identifier generator.

    python tests/test_module1_topology.py     (no dependencies)
    pytest tests/test_module1_topology.py

Acceptance criteria (from the roadmap): the hierarchy is well-formed (every home
traces a complete path to content), the identifiers are authentic MIGA-style codes,
the regional weights produce the right distribution, the structure actually permits
the cluster/path/source shapes, the network is mid-scale yet visualisable, and the
same config reproduces the same graph exactly.
"""

from __future__ import annotations

import os
import re
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import traceback

import si_demo.core as c
from si_demo.topology import Membership, Node, ServiceGraph, build_service_graph


def _default():
    return build_service_graph(c.default_config())


def _tiny():
    return build_service_graph(c.tiny_config())


# ---------------------------------------------------------------------------
# 1. Well-formedness - every home traces a complete path to content
# ---------------------------------------------------------------------------

def test_every_stb_has_complete_membership_path():
    g = _default()
    assert len(g.stb_ids) > 0
    for stb in g.stb_ids:
        m = g.stb_membership[stb]
        # the full path is populated and every entity exists in the graph
        for entity in m.path():
            assert entity in g.nodes, f"path entity {entity} missing from graph"
        # the path has the right length: stb, ont, olt, agg, bng, route, cdn, content
        assert len(m.path()) == 8


def test_access_parent_chain_is_consistent():
    g = _default()
    for stb in g.stb_ids:
        m = g.stb_membership[stb]
        # node parent links must agree with the membership: STB->ONT->OLT->AGG->BNG
        assert g.nodes[m.stb_id].parent_id == m.ont_id
        assert g.nodes[m.ont_id].parent_id == m.olt_id
        assert g.nodes[m.olt_id].parent_id == m.agg_id
        assert g.nodes[m.agg_id].parent_id == m.bng_id
        assert g.nodes[m.bng_id].parent_id == m.route_id


def test_layers_are_assigned_correctly():
    g = _default()
    expect = {
        c.EntityType.STB: c.Layer.HOME, c.EntityType.ONT: c.Layer.ACCESS,
        c.EntityType.OLT: c.Layer.ACCESS, c.EntityType.AGG: c.Layer.CORE,
        c.EntityType.BNG: c.Layer.CORE, c.EntityType.CORE: c.Layer.CORE,
        c.EntityType.CDN_EDGE: c.Layer.CONTENT, c.EntityType.CONTENT: c.Layer.CONTENT,
    }
    for n in g.nodes.values():
        assert n.layer == expect[n.entity_type], f"{n.entity_id}: wrong layer"


def test_reverse_indices_cover_all_stbs():
    g = _default()
    assert sum(len(v) for v in g.stbs_by_olt.values()) == len(g.stb_ids)
    assert sum(len(v) for v in g.stbs_by_route.values()) == len(g.stb_ids)
    assert sum(len(v) for v in g.stbs_by_content.values()) == len(g.stb_ids)


# ---------------------------------------------------------------------------
# 2. Authentic MIGA-style identifiers
# ---------------------------------------------------------------------------

def test_central_office_codes_are_7_digit_miga_style():
    g = _default()
    province_codes = {r.province_code for r in c.default_config().regions}
    centrals = {n.central_id for n in g.nodes.values() if n.central_id}
    assert centrals, "expected central office codes on OLTs/homes"
    for cid in centrals:
        assert re.fullmatch(r"\d{7}", cid), f"central id {cid} not 7 digits"
        assert cid[:2] in province_codes, f"central id {cid} has unknown province prefix"


def test_olt_ids_follow_authentic_pattern():
    g = _default()
    for olt in g.olt_ids:
        # e.g. OLT-2807001-03
        assert re.fullmatch(r"OLT-\d{7}-\d{2,}", olt), f"OLT id {olt} not authentic"
        assert g.nodes[olt].identity["olt_model"] == "MA5600T"


def test_stb_and_household_ids_are_authentic():
    g = _default()
    sample = g.stb_ids[:50]
    for stb in sample:
        assert re.fullmatch(r"STB-\d{7}-\d+-\d{3}", stb), f"STB id {stb} not authentic"
        hh = g.stb_membership[stb].household_id
        assert hh.startswith("HH-")


def test_multicast_groups_in_admin_scoped_range():
    g = _default()
    for content in g.content_ids:
        mcast = g.nodes[content].identity["multicast_group_id"]
        assert mcast.startswith("239."), f"multicast {mcast} not in 239/8 IPTV range"
        assert g.nodes[content].identity["channel_name"]


def test_cdn_edges_named_by_city_and_madrid_has_two():
    g = build_service_graph(c.default_config())
    # Madrid should carry two CDN edges (MAD-1, MAD-2) per its larger footprint.
    mad = [e for e in g.cdn_edge_ids if e.startswith("CDN-MAD-")]
    assert len(mad) >= 2, f"expected >=2 Madrid CDN edges, got {mad}"


# ---------------------------------------------------------------------------
# 3. Regional distribution follows the configured weights
# ---------------------------------------------------------------------------

def test_madrid_largest_and_acoruna_smallest():
    g = _default()
    by_region = {}
    for stb in g.stb_ids:
        reg = g.stb_membership[stb].region
        by_region[reg] = by_region.get(reg, 0) + 1
    assert by_region["Madrid metro"] == max(by_region.values()), "Madrid should be largest"
    assert by_region["A Coruna"] == min(by_region.values()), "A Coruna should be smallest"


def test_province_codes_match_regions():
    g = _default()
    code_by_region = {r.name: r.province_code for r in c.default_config().regions}
    for stb in g.stb_ids[:200]:
        m = g.stb_membership[stb]
        assert m.province_code == code_by_region[m.region]
        assert m.central_id[:2] == m.province_code


# ---------------------------------------------------------------------------
# 4. Shape-readiness - the structure must permit cluster, path and source faults
# ---------------------------------------------------------------------------

def test_cluster_shape_is_possible():
    # At least one OLT must host enough homes for a cluster shape to form.
    g = _default()
    biggest = max(len(v) for v in g.stbs_by_olt.values())
    assert biggest >= 10, f"largest OLT has only {biggest} homes; cluster too small"


def test_source_shape_hits_otherwise_unrelated_homes():
    # A content source must be watched by homes spanning multiple OLTs, so a content
    # fault impairs otherwise-unrelated homes (the SOURCE shape, distinct from CLUSTER).
    g = _default()
    spans = []
    for content, homes in g.stbs_by_content.items():
        olts = {g.stb_membership[s].olt_id for s in homes}
        spans.append(len(olts))
    assert max(spans) >= 3, "no content source spans multiple OLTs; SOURCE not separable"


def test_path_shape_spans_multiple_olts():
    # A core route must carry homes from multiple OLTs, so a core fault forms a path
    # across access nodes (distinct from a single-OLT cluster).
    g = _default()
    spans = []
    for route, homes in g.stbs_by_route.items():
        olts = {g.stb_membership[s].olt_id for s in homes}
        spans.append(len(olts))
    assert max(spans) >= 3, "no route spans multiple OLTs; PATH not separable"


def test_content_assignment_independent_of_olt():
    # Within one OLT, homes should not all watch the same channel; content is assigned
    # independently of access path, which is what separates SOURCE from CLUSTER.
    g = _default()
    big_olt = max(g.stbs_by_olt, key=lambda o: len(g.stbs_by_olt[o]))
    channels = {g.stb_membership[s].content_id for s in g.stbs_by_olt[big_olt]}
    assert len(channels) > 1, "all homes on one OLT watch one channel; assignment not independent"


# ---------------------------------------------------------------------------
# 5. Scale and the peers accessor
# ---------------------------------------------------------------------------

def test_scale_is_mid_sized():
    g = _default()
    assert 1000 <= len(g.stb_ids) <= 10000, "default network should be thousands of STBs"


def test_peers_on_olt_excludes_self_and_shares_olt():
    g = _default()
    big_olt = max(g.stbs_by_olt, key=lambda o: len(g.stbs_by_olt[o]))
    a_home = g.stbs_by_olt[big_olt][0]
    peers = g.peers_on_olt(a_home)
    assert a_home not in peers
    for p in peers:
        assert g.stb_membership[p].olt_id == big_olt


# ---------------------------------------------------------------------------
# 6. The four-field boundary is preserved - Module 1 emits no magnitudes
# ---------------------------------------------------------------------------

def test_topology_carries_no_magnitudes():
    g = _tiny()
    # No node identity may carry a per-interval flow value; identity is static only.
    forbidden = {"magnitude", "freeze_duration", "port_utilization", "transport_load"}
    for n in g.nodes.values():
        leaked = forbidden & set(n.identity.keys())
        assert not leaked, f"{n.entity_id} identity leaked flow fields {leaked}"


# ---------------------------------------------------------------------------
# 7. Determinism - same config reproduces the same graph exactly
# ---------------------------------------------------------------------------

def test_same_config_same_graph():
    g1 = build_service_graph(c.tiny_config())
    g2 = build_service_graph(c.tiny_config())
    assert g1.stb_ids == g2.stb_ids
    assert g1.olt_ids == g2.olt_ids
    assert list(g1.nodes.keys()) == list(g2.nodes.keys())
    # memberships identical
    for stb in g1.stb_ids:
        assert g1.stb_membership[stb] == g2.stb_membership[stb]


def test_different_seed_different_graph_detail():
    import dataclasses
    cfg_a = c.tiny_config(seed=111)
    cfg_b = c.tiny_config(seed=222)
    ga = build_service_graph(cfg_a)
    gb = build_service_graph(cfg_b)
    # content assignments (seeded) should differ somewhere, even if topology shape matches
    a_assign = [ga.stb_membership[s].content_id for s in ga.stb_ids]
    b_assign = [gb.stb_membership[s].content_id for s in gb.stb_ids]
    assert a_assign != b_assign


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
    print(f"\nModule 1 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
