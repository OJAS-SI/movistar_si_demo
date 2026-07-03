"""
Module 2 - Telemetry and baseline generator.

Over the static service graph, this produces a continuous, regularly-sampled stream
in BOTH record types, for a HEALTHY network. It is the reference a fault deviates
from; Module 3 perturbs this stream to inject faults.

THE CORE STREAM (what the SI engine reads - exactly four fields per record).
Each home depends on three subsystems, and a fault in one must not pollute the
others, so each home emits three independent quality signals per interval, one per
subsystem edge:

    (STB -> OLT,     magnitude = access impairment)      rises on an access fault
    (STB -> route,   magnitude = transport impairment)   rises on a core fault
    (STB -> content, magnitude = content impairment)     rises on a content fault

Impairment is a non-negative severity (0 = perfect service; higher = worse, in
freeze/buffering-second-equivalents). When healthy it sits on a low per-home
baseline with natural noise and prime-time seasonality, so an injected fault must
be told apart from normal variation, not from silence. Because the three signals
are independent, an OLT fault raises only the access edges of that OLT's homes and
leaves route and content flat - which is precisely what lets the engine attribute a
fault to its true layer.

THE ENRICHMENT STREAM (never an SI input - joined only at report time).
Alongside the core stream, the generator populates the full per-layer field set
from the data dictionary for every entity every interval (freeze_duration,
port_utilization, transport_load, segment_failures, wifi_snr, and so on). This is
what lets a diagnosis read in operator language. The SI engine never sees it.

Module 2 generates a fault-free world: every magnitude stays within its healthy
band. With no faults, the engine downstream therefore raises nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Tuple

from .core import (
    CoreRecord, DemoConfig, EnrichmentRecord, EntityType, Layer, SeededRandom,
    make_core_record,
)
from .topology import ServiceGraph


# The three subsystem edges a home emits on. Classified by the destination entity:
# an OLT (access), a core route (core/transport), or a content source (content).
ACCESS = "access"
TRANSPORT = "transport"
CONTENT = "content"


@dataclass(frozen=True, slots=True)
class HomeBaseline:
    """A home's stable, per-subsystem healthy impairment levels and its own noisiness.
    Generated once per home; constant across the run."""
    access_base: float
    transport_base: float
    content_base: float
    noisiness: float


@dataclass
class IntervalTelemetry:
    """All telemetry for one interval: the four-field core records the SI engine
    reads, and the enrichment records (keyed by entity_id) joined only at report
    time. core_index lets Module 3 find and perturb a specific home/subsystem edge."""
    timestamp: int
    core: List[CoreRecord]
    enrichment: Dict[str, EnrichmentRecord]
    core_index: Dict[Tuple[str, str], int] = field(default_factory=dict)

    def core_record_for(self, stb_id: str, dst_id: str) -> int:
        """Index into `core` of the record (stb_id -> dst_id), or -1 if absent."""
        return self.core_index.get((stb_id, dst_id), -1)


class TelemetryGenerator:
    """Generates healthy telemetry over a ServiceGraph, deterministically from the
    config seed. interval(t) is a pure function of t (reproducible regardless of call
    order); stream() yields every interval of the run in order."""

    # Healthy impairment ceiling: a home's healthy signal stays comfortably below
    # this. Faults (Module 3) push well above it. Used by the standalone test.
    HEALTHY_CEILING = 2.5

    def __init__(self, graph: ServiceGraph, config: DemoConfig) -> None:
        self.graph = graph
        self.config = config
        self._seed = config.seed
        # Per-home baselines, drawn once in a fixed order for reproducibility.
        base_rng = SeededRandom(self._seed).child("telemetry.baselines")
        self.home_baseline: Dict[str, HomeBaseline] = {}
        for stb in graph.stb_ids:
            self.home_baseline[stb] = HomeBaseline(
                access_base=base_rng.uniform(0.2, 0.8),
                transport_base=base_rng.uniform(0.15, 0.6),
                content_base=base_rng.uniform(0.15, 0.6),
                noisiness=base_rng.uniform(0.10, 0.25))

    # ----- seasonality -----

    def seasonality(self, t: int) -> float:
        """A mild multiplicative load factor by time of day: prime-time intervals
        carry more load and so slightly more impairment. This is the natural
        variation a real fault must be distinguished from."""
        iod = t % self.config.intervals_per_day
        if self.config.prime_time_start <= iod < self.config.prime_time_end:
            return 1.35
        # a gentle daily swell either side of prime time
        if self.config.prime_time_start - 24 <= iod < self.config.prime_time_end + 24:
            return 1.12
        return 1.0

    # ----- healthy magnitude for one home/subsystem at one interval -----

    def base_magnitude(self, stb_id: str, subsystem: str, t: int) -> float:
        """The healthy impairment for a home on a subsystem at interval t: baseline,
        scaled by seasonality, plus reproducible per-interval noise, floored at 0.
        Module 3 adds fault deltas on top of this."""
        hb = self.home_baseline[stb_id]
        base = {ACCESS: hb.access_base, TRANSPORT: hb.transport_base,
                CONTENT: hb.content_base}[subsystem]
        rng = SeededRandom(self._seed).child(f"telemetry.noise.{t}.{subsystem}.{stb_id}")
        noise = rng.gauss(0.0, hb.noisiness)
        val = base * self.seasonality(t) + noise
        return max(0.0, val)

    # ----- one interval of healthy telemetry -----

    def interval(self, t: int) -> IntervalTelemetry:
        graph = self.graph
        core: List[CoreRecord] = []
        core_index: Dict[Tuple[str, str], int] = {}
        enrichment: Dict[str, EnrichmentRecord] = {}

        # 1. Core stream: three subsystem edges per home.
        for stb in graph.stb_ids:
            m = graph.stb_membership[stb]
            for subsystem, dst in ((ACCESS, m.olt_id), (TRANSPORT, m.route_id),
                                   (CONTENT, m.content_id)):
                mag = self.base_magnitude(stb, subsystem, t)
                core_index[(stb, dst)] = len(core)
                core.append(make_core_record(stb, dst, t, mag))

        # 2. Enrichment stream: per-entity, per-interval flow + identity, healthy.
        #    Generated for the entities a diagnosis may reference (homes and the
        #    nodes on their paths), which is every node in the graph.
        season = self.seasonality(t)
        for stb in graph.stb_ids:
            m = graph.stb_membership[stb]
            idy = graph.nodes[stb].identity
            acc = self.base_magnitude(stb, ACCESS, t)
            con = self.base_magnitude(stb, CONTENT, t)
            enrichment[stb] = EnrichmentRecord(
                entity_id=stb, timestamp=t, entity_type=EntityType.STB, layer=Layer.HOME,
                fields={"freeze_duration": round(acc + con, 3), "reboot_count": 0,
                        "startup_delay": round(0.8 + 0.2 * season, 3),
                        "error_code": None, "firmware_version": idy["firmware_version"],
                        "household_id": idy["household_id"], "service_tier": idy["service_tier"],
                        "region": idy["region"], "central_office": idy["central_office"],
                        "watching_content": idy["watching_content"],
                        "multicast_group_id": idy["multicast_group_id"]})

        # OLT enrichment (port utilization rises mildly during prime time).
        for olt in graph.olt_ids:
            n_homes = len(graph.stbs_by_olt.get(olt, []))
            util = min(0.95, 0.45 * season + 0.0008 * n_homes)
            enrichment[olt] = EnrichmentRecord(
                entity_id=olt, timestamp=t, entity_type=EntityType.OLT, layer=Layer.ACCESS,
                fields={"port_utilization": round(util, 3), "line_snr": 34.0,
                        "fec_errors": 0, "optical_rx_power": -18.5,
                        "olt_model": graph.nodes[olt].identity["olt_model"],
                        "central_office": graph.nodes[olt].identity["central_office"]})

        # Core route enrichment.
        for route in graph.route_ids:
            load = min(0.9, 0.4 * season)
            enrichment[route] = EnrichmentRecord(
                entity_id=route, timestamp=t, entity_type=EntityType.CORE, layer=Layer.CORE,
                fields={"transport_load": round(load, 3), "path_latency_ms": round(7 * season, 2),
                        "queue_depth": int(20 * season), "jitter_ms": round(0.6 * season, 2),
                        "ecmp_path": graph.nodes[route].identity["ecmp_path"]})

        # Content / CDN enrichment.
        for content in graph.content_ids:
            enrichment[content] = EnrichmentRecord(
                entity_id=content, timestamp=t, entity_type=EntityType.CONTENT, layer=Layer.CONTENT,
                fields={"segment_failures": 0, "cache_hit_ratio": round(0.97 - 0.02 * (season - 1), 3),
                        "encoder_dropped_frm": 0,
                        "channel_name": graph.nodes[content].identity["channel_name"],
                        "multicast_group_id": graph.nodes[content].identity["multicast_group_id"],
                        "serving_cdn_edge": graph.nodes[content].identity["serving_cdn_edge"]})

        return IntervalTelemetry(timestamp=t, core=core, enrichment=enrichment,
                                 core_index=core_index)

    def stream(self) -> Iterator[IntervalTelemetry]:
        """Yield healthy telemetry for every interval of the run, in order."""
        for t in range(self.config.run_intervals):
            yield self.interval(t)
