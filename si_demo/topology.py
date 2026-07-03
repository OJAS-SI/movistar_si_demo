"""
Module 1 - Topology and identifier generator.

Builds the static service graph once per run: the Telefonica-style GPON/FTTH
hierarchy across the six Spanish metro regions, with authentic MIGA-style
identifiers, and the per-home membership index that makes the four fault shapes
computable downstream.

The hierarchy, in path order from the home up toward the content origin:
    STB -> ONT -> OLT (in a central office) -> aggregation switch -> BNG
        -> core/transport route -> CDN edge -> content (encoder / multicast group)

Why three kinds of membership per home. A fault's shape on the graph is read from
what the affected homes share:
    a single home alone                 -> SINGLE  -> home layer
    homes behind one OLT                -> CLUSTER -> access layer
    homes whose traffic shares a route  -> PATH    -> core layer
    homes watching one content source   -> SOURCE  -> content layer
So every set-top box records its OLT (access chain), its core route, and its
content assignment. Module 1 provides exactly this structure plus the identifiers.

THE FOUR-FIELD BOUNDARY. This module produces only static identity and static
identity-enrichment (region, province code, OLT model, firmware, multicast group,
channel name). It emits no magnitudes; the per-interval flow values that the SI
engine scores arrive in Module 2. Identity-enrichment lives in Node.identity and
is for the operator report only, never an SI input. The central office is carried
as an attribute, not a node: it is a grouping label, not something the SI engine
reasons over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .core import DemoConfig, EntityType, Layer, SeededRandom, default_config


# ---------------------------------------------------------------------------
# Authentic naming helpers
# ---------------------------------------------------------------------------

_CITY_CODE = {
    "Madrid metro": "MAD", "Barcelona metro": "BCN", "Valencia": "VLC",
    "Sevilla": "SVQ", "Bilbao": "BIO", "A Coruna": "LCG",
}
_CHANNEL_POOL = [
    "LALIGA", "CHAMPIONS", "EUROPA", "CONFERENCE", "MOVISTAR-PLUS", "SERIES",
    "CINE", "DEPORTES", "DOCU", "INFANTIL", "NOTICIAS", "MULTIDEPORTE",
]
_FIRMWARE_POOL = ["3.10", "3.11", "3.12", "3.14", "4.02"]
_SERVICE_TIERS = ["Fusion", "Fusion Plus", "Fusion Total", "miMovistar"]


def _city_code(region_name: str) -> str:
    return _CITY_CODE.get(region_name, region_name[:3].upper())


# ---------------------------------------------------------------------------
# Node and membership records
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Node:
    """One entity in the service graph: its identity, its place in the hierarchy,
    and its static identity-enrichment. parent_id is the access-tree parent (the
    node immediately upstream toward the content origin); None for content sources."""
    entity_id: str
    entity_type: EntityType
    layer: Layer
    parent_id: Optional[str]
    region: str
    province_code: str
    central_id: Optional[str]
    identity: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Membership:
    """The full path membership of one set-top box. This is the shared-structure
    index the SI engine reads to localize a fault to a layer."""
    stb_id: str
    household_id: str
    ont_id: str
    olt_id: str
    central_id: str
    agg_id: str
    bng_id: str
    route_id: str
    cdn_edge_id: str
    content_id: str
    multicast_group_id: str
    region: str
    province_code: str

    def path(self) -> Tuple[str, ...]:
        return (self.stb_id, self.ont_id, self.olt_id, self.agg_id, self.bng_id,
                self.route_id, self.cdn_edge_id, self.content_id)


@dataclass
class ServiceGraph:
    """The complete static service graph for one run, plus the indices later modules
    need. Built by build_service_graph(config)."""
    config: DemoConfig
    nodes: Dict[str, Node]
    access_children: Dict[str, List[str]]
    stb_membership: Dict[str, Membership]
    stbs_by_olt: Dict[str, List[str]]
    stbs_by_route: Dict[str, List[str]]
    stbs_by_content: Dict[str, List[str]]
    stb_ids: List[str]
    olt_ids: List[str]
    route_ids: List[str]
    content_ids: List[str]
    cdn_edge_ids: List[str]

    def node(self, entity_id: str) -> Node:
        return self.nodes[entity_id]

    def peers_on_olt(self, stb_id: str) -> List[str]:
        """Other set-top boxes behind the same OLT. Used by UC2 to confirm a decline
        is home-isolated (peers healthy)."""
        olt = self.stb_membership[stb_id].olt_id
        return [s for s in self.stbs_by_olt[olt] if s != stb_id]

    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for n in self.nodes.values():
            counts[n.entity_type.value] = counts.get(n.entity_type.value, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# The generator
# ---------------------------------------------------------------------------

def _alloc_stb_counts(config: DemoConfig) -> Dict[str, int]:
    """Distribute the target number of set-top boxes across regions by weight, with
    at least one full OLT's worth of homes per region."""
    total_w = config.total_region_weight()
    counts: Dict[str, int] = {}
    for r in config.regions:
        n = int(round(config.n_stb_target * (r.weight / total_w)))
        counts[r.name] = max(n, config.topology.homes_per_olt_typical)
    return counts


def _chunk(seq: List[str], size: int) -> List[List[str]]:
    return [seq[i:i + size] for i in range(0, len(seq), max(size, 1))]


def build_service_graph(config: Optional[DemoConfig] = None) -> ServiceGraph:
    """Construct the static, Spain-grounded service graph deterministically. The
    same config (hence the same seed) always yields the same graph, identifiers and
    memberships. Nodes are created once, with correct parents, in a single pass."""
    config = config or default_config()
    rng = SeededRandom(config.seed).child("topology")
    topo = config.topology

    nodes: Dict[str, Node] = {}
    access_children: Dict[str, List[str]] = {}
    stb_membership: Dict[str, Membership] = {}

    def add_node(node: Node) -> None:
        nodes[node.entity_id] = node
        access_children.setdefault(node.entity_id, [])
        if node.parent_id is not None:
            access_children.setdefault(node.parent_id, []).append(node.entity_id)

    # --- 1. Content sources and the CDN edges that serve them ---
    cdn_edge_ids: List[str] = []
    cdn_plan: List[str] = []
    for r in config.regions:
        cdn_plan.append(_city_code(r.name))
        if r.name == "Madrid metro":
            cdn_plan.append(_city_code(r.name))   # Madrid carries two edges
    if topo.n_cdn_edges:
        cdn_plan = cdn_plan[: topo.n_cdn_edges]
    seen_city: Dict[str, int] = {}
    for city in cdn_plan:
        seen_city[city] = seen_city.get(city, 0) + 1
        cdn_id = f"CDN-{city}-{seen_city[city]}"
        cdn_edge_ids.append(cdn_id)
        add_node(Node(cdn_id, EntityType.CDN_EDGE, Layer.CONTENT, None,
                      "(national)", "00", None, {"edge_site": city}))

    content_ids: List[str] = []
    for i in range(max(topo.n_content_sources, 1)):
        channel = _CHANNEL_POOL[i % len(_CHANNEL_POOL)]
        content_id = f"CH-{channel}"
        mcast = f"239.{10 + i}.{1 + (i % 5)}.{1 + i}"
        serving_cdn = cdn_edge_ids[i % len(cdn_edge_ids)]
        content_ids.append(content_id)
        add_node(Node(content_id, EntityType.CONTENT, Layer.CONTENT, serving_cdn,
                      "(national)", "00", None,
                      {"channel_name": channel, "multicast_group_id": mcast,
                       "encoder_id": f"ENC-{channel}-1", "codec": "HEVC",
                       "bitrate_mbps": rng.randint(8, 18), "serving_cdn_edge": serving_cdn}))

    # --- 2. Core/transport routes ---
    route_ids: List[str] = []
    for i in range(max(topo.n_core_paths, 1)):
        route_id = f"RT-CORE-{i + 1:02d}"
        egress = cdn_edge_ids[i % len(cdn_edge_ids)]
        route_ids.append(route_id)
        add_node(Node(route_id, EntityType.CORE, Layer.CORE, egress,
                      "(national)", "00", None,
                      {"ecmp_path": f"ecmp-{i + 1}",
                       "link_capacity_gbps": rng.choice([100, 200, 400]),
                       "primary_egress": egress}))

    # --- 3. Per-region access tree, built parent-first so nodes are created once ---
    stb_counts = _alloc_stb_counts(config)
    olt_ids: List[str] = []
    stb_ids: List[str] = []
    route_cursor = 0

    for r in config.regions:
        want = stb_counts[r.name]
        centrals = list(r.central_office_names)
        central_codes = [f"{r.province_code}{(ci + 1):05d}" for ci in range(len(centrals))]
        n_olts = max(1, -(-want // topo.homes_per_olt_typical))   # ceil division

        # Plan the OLT list first (each assigned to a central office, round-robin).
        region_olts: List[Tuple[str, str, str]] = []   # (olt_id, central_id, central_name)
        for k in range(n_olts):
            cidx = k % len(centrals)
            central_id = central_codes[cidx]
            olt_id = f"OLT-{central_id}-{k + 1:02d}"
            region_olts.append((olt_id, central_id, centrals[cidx]))

        # Plan AGG grouping (homes_per_agg OLTs per aggregation switch).
        olt_id_list = [o[0] for o in region_olts]
        agg_groups = _chunk(olt_id_list, topo.homes_per_agg)
        olt_to_agg: Dict[str, str] = {}
        agg_ids: List[str] = []
        for ai, group in enumerate(agg_groups):
            agg_id = f"AGG-{r.province_code}-{ai + 1:02d}"
            agg_ids.append(agg_id)
            for olt_id in group:
                olt_to_agg[olt_id] = agg_id

        # Plan BNG grouping (aggs_per_bng AGGs per BNG); assign each BNG a route.
        bng_groups = _chunk(agg_ids, topo.aggs_per_bng)
        agg_to_bng: Dict[str, str] = {}
        bng_route: Dict[str, str] = {}
        bng_ids: List[str] = []
        for bi, group in enumerate(bng_groups):
            bng_id = f"BNG-{r.province_code}-{bi + 1:02d}"
            route_id = route_ids[route_cursor % len(route_ids)]
            route_cursor += 1
            bng_ids.append(bng_id)
            bng_route[bng_id] = route_id
            for agg_id in group:
                agg_to_bng[agg_id] = bng_id

        # Now create the BNG, AGG and OLT nodes once, with correct parents.
        for bng_id in bng_ids:
            add_node(Node(bng_id, EntityType.BNG, Layer.CORE, bng_route[bng_id],
                          r.name, r.province_code, None,
                          {"bng_role": "broadband_network_gateway",
                           "uplink_route": bng_route[bng_id]}))
        for agg_id in agg_ids:
            add_node(Node(agg_id, EntityType.AGG, Layer.CORE, agg_to_bng[agg_id],
                          r.name, r.province_code, None,
                          {"agg_role": "aggregation_switch"}))
        for olt_id, central_id, central_name in region_olts:
            olt_ids.append(olt_id)
            add_node(Node(olt_id, EntityType.OLT, Layer.ACCESS, olt_to_agg[olt_id],
                          r.name, r.province_code, central_id,
                          {"olt_model": "MA5600T", "central_office": central_name,
                           "max_homes": topo.olt_max_homes}))

        # Populate homes (ONT + STB) under each OLT until the region quota is met.
        made_homes = 0
        for olt_id, central_id, central_name in region_olts:
            if made_homes >= want:
                break
            agg_id = olt_to_agg[olt_id]
            bng_id = agg_to_bng[agg_id]
            route_id = bng_route[bng_id]
            homes_here = min(topo.homes_per_olt_typical, want - made_homes)
            olt_suffix = olt_id.split("-")[-1]
            for h in range(homes_here):
                made_homes += 1
                home_tag = f"{olt_suffix}-{h + 1:03d}"
                household_id = f"HH-{central_id}-{home_tag}"
                device_id = f"STB-{central_id}-{home_tag}"
                ont_id = f"ONT-{central_id}-{home_tag}"
                content_id = rng.choice(content_ids)       # independent of access path
                mcast = nodes[content_id].identity["multicast_group_id"]
                cdn_edge_id = nodes[content_id].identity["serving_cdn_edge"]

                add_node(Node(ont_id, EntityType.ONT, Layer.ACCESS, olt_id,
                              r.name, r.province_code, central_id,
                              {"household_id": household_id}))
                add_node(Node(device_id, EntityType.STB, Layer.HOME, ont_id,
                              r.name, r.province_code, central_id,
                              {"household_id": household_id,
                               "account_id": f"AC-{rng.randint(10_000_000, 99_999_999)}",
                               "firmware_version": rng.choice(_FIRMWARE_POOL),
                               "service_tier": rng.choice(_SERVICE_TIERS),
                               "tenure_months": rng.randint(2, 180),
                               "watching_content": content_id, "multicast_group_id": mcast,
                               "cdn_edge_id": cdn_edge_id, "olt_id": olt_id,
                               "central_id": central_id, "central_office": central_name,
                               "region": r.name, "province_code": r.province_code}))
                stb_ids.append(device_id)
                stb_membership[device_id] = Membership(
                    stb_id=device_id, household_id=household_id, ont_id=ont_id,
                    olt_id=olt_id, central_id=central_id, agg_id=agg_id, bng_id=bng_id,
                    route_id=route_id, cdn_edge_id=cdn_edge_id, content_id=content_id,
                    multicast_group_id=mcast, region=r.name, province_code=r.province_code)

    # --- 4. Reverse indices (the shared-structure groupings) ---
    stbs_by_olt: Dict[str, List[str]] = {}
    stbs_by_route: Dict[str, List[str]] = {}
    stbs_by_content: Dict[str, List[str]] = {}
    for stb_id, m in stb_membership.items():
        stbs_by_olt.setdefault(m.olt_id, []).append(stb_id)
        stbs_by_route.setdefault(m.route_id, []).append(stb_id)
        stbs_by_content.setdefault(m.content_id, []).append(stb_id)

    return ServiceGraph(
        config=config, nodes=nodes, access_children=access_children,
        stb_membership=stb_membership, stbs_by_olt=stbs_by_olt,
        stbs_by_route=stbs_by_route, stbs_by_content=stbs_by_content,
        stb_ids=stb_ids, olt_ids=olt_ids, route_ids=route_ids,
        content_ids=content_ids, cdn_edge_ids=cdn_edge_ids)
