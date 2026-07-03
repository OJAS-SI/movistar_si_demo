"""
Module 0 - Configuration schema and the canonical default.

DemoConfig is the single, frozen description of a demo run: the random seed, the
Spanish regional structure, the network scale, the interval cadence, and the run
length. Every module receives the same DemoConfig, so a run is fully determined by
it. default_config() builds the canonical configuration grounded in Telefonica's
public Spanish footprint, exactly as the specification describes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True, slots=True)
class RegionConfig:
    """One Spanish metro region, anchored on one or more central offices (centrales)
    that house the OLTs. province_code is the leading pair of Telefonica's 7-digit
    MIGA central-office identifier (28 = Madrid, 08 = Barcelona, and so on), and is
    reproduced in the synthetic node IDs so they read authentically. weight sets the
    region's relative size in the network."""
    name: str
    province_code: str
    central_office_names: Tuple[str, ...]
    weight: float


@dataclass(frozen=True, slots=True)
class TopologyConfig:
    """The fan-out structure of the GPON/FTTH hierarchy. These shape how many homes
    sit behind each OLT, how OLTs aggregate, and how the core and CDN are laid out.
    Chosen so the network is large enough for genuine cluster, path, and source
    shapes to emerge, yet small enough to visualise."""
    olt_max_homes: int = 3500           # Huawei MA5600T-class capacity (upper bound)
    homes_per_olt_typical: int = 60     # modelled homes behind one OLT in the demo
    olts_per_central_typical: int = 3   # OLTs in a central office
    homes_per_agg: int = 4              # OLTs per aggregation switch (fan-in)
    aggs_per_bng: int = 3               # aggregation switches per BNG
    n_core_paths: int = 4               # distinct core/transport routes
    n_cdn_edges: int = 5                # CDN edges serving content
    n_content_sources: int = 8          # encoders / channel groups (multicast)


@dataclass(frozen=True, slots=True)
class DemoConfig:
    """The complete, frozen description of one demo run."""
    seed: int
    regions: Tuple[RegionConfig, ...]
    topology: TopologyConfig
    n_stb_target: int           # approximate total set-top boxes (mid-scale: thousands)
    interval_seconds: int       # cadence of the regularly-sampled stream
    run_intervals: int          # number of intervals in a run
    prime_time_start: int       # interval-of-day where prime-time load begins
    prime_time_end: int         # interval-of-day where prime-time load ends
    intervals_per_day: int      # for seasonality cycling

    def total_region_weight(self) -> float:
        return sum(r.weight for r in self.regions)


# The six real Telefonica metro regions named in the specification, with their
# province codes and indicative weightings.
CANONICAL_REGIONS: Tuple[RegionConfig, ...] = (
    RegionConfig("Madrid metro",    "28", ("Las Tablas", "La Concepcion", "Pozuelo"), weight=4.0),
    RegionConfig("Barcelona metro", "08", ("Eixample", "Terrassa"),                   weight=3.0),
    RegionConfig("Valencia",        "46", ("Valencia centro",),                       weight=2.0),
    RegionConfig("Sevilla",         "41", ("Sevilla centro",),                        weight=2.0),
    RegionConfig("Bilbao",          "48", ("Bilbao centro",),                         weight=1.5),
    RegionConfig("A Coruna",        "15", ("A Coruna centro",),                       weight=1.0),
)


def default_config(seed: int = 20260629) -> DemoConfig:
    """Build the canonical demo configuration: the six-region Spanish network at
    mid scale, sampled around the clock, grounded in Telefonica's public footprint.

    n_stb_target is on the order of a few thousand, which the specification calls
    for: large enough for genuine shapes, small enough to visualise. The default
    run covers a couple of simulated days at a coarse interval so faults, decoys,
    and healthy stretches all fit in one demo loop.
    """
    return DemoConfig(
        seed=seed,
        regions=CANONICAL_REGIONS,
        topology=TopologyConfig(),
        n_stb_target=2400,
        interval_seconds=300,        # a five-minute interval
        run_intervals=576,           # 576 intervals = 2 simulated days at 5-min cadence
        prime_time_start=240,        # ~20:00 on a 5-min, midnight-anchored day
        prime_time_end=276,          # ~23:00
        intervals_per_day=288,       # 24h / 5min
    )


def tiny_config(seed: int = 20260629) -> DemoConfig:
    """A deliberately small configuration for fast standalone and integration tests:
    a couple of regions, a handful of OLTs, a short run. Same contracts, small size."""
    small_regions = (
        RegionConfig("Madrid metro",    "28", ("Las Tablas",), weight=2.0),
        RegionConfig("A Coruna",        "15", ("A Coruna centro",), weight=1.0),
    )
    return DemoConfig(
        seed=seed,
        regions=small_regions,
        topology=TopologyConfig(homes_per_olt_typical=12, olts_per_central_typical=2,
                                homes_per_agg=2, aggs_per_bng=2, n_core_paths=2,
                                n_cdn_edges=2, n_content_sources=3),
        n_stb_target=48,
        interval_seconds=300,
        run_intervals=60,
        prime_time_start=24,
        prime_time_end=30,
        intervals_per_day=288,
    )
