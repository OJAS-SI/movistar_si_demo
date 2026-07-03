"""
Module 0 - Shared Foundations and Contracts.

This package is the frozen vocabulary of the Movistar Structural Intelligence demo.
Every later module (topology, telemetry, fault injection, the SI engine, the
diagnosis formatter, the scoring harness, the console, the orchestrator) imports
its contracts from here and depends on their stability.

Public surface (import these; do not reach into submodules):

    Records and the four-field boundary:
        CoreRecord, make_core_record, CORE_RECORD_FIELDS
        EnrichmentRecord

    SI output (explainable diagnosis):
        Diagnosis, Evidence, Provenance, PredictedTrajectory

    Ground truth and scoring:
        GroundTruthLabel, Score

    Enumerations:
        Layer, EntityType, Shape, UseCase, RampProfile, SHAPE_TO_LAYER

    Configuration and determinism:
        DemoConfig, RegionConfig, TopologyConfig
        default_config, tiny_config, CANONICAL_REGIONS
        SeededRandom

    Contract guards:
        FROZEN_CONTRACT_VERSION
        assert_four_field_boundary, assert_core_stream_clean
"""

from __future__ import annotations

from .types import (
    CoreRecord, make_core_record, CORE_RECORD_FIELDS,
    EnrichmentRecord,
    Diagnosis, Evidence, Provenance, PredictedTrajectory,
    GroundTruthLabel, Score,
    Layer, EntityType, Shape, UseCase, RampProfile, SHAPE_TO_LAYER,
)
from .config import (
    DemoConfig, RegionConfig, TopologyConfig,
    default_config, tiny_config, CANONICAL_REGIONS,
)
from .rng import SeededRandom
from .contracts import (
    FROZEN_CONTRACT_VERSION,
    assert_four_field_boundary, assert_core_stream_clean,
)

__all__ = [
    "CoreRecord", "make_core_record", "CORE_RECORD_FIELDS",
    "EnrichmentRecord",
    "Diagnosis", "Evidence", "Provenance", "PredictedTrajectory",
    "GroundTruthLabel", "Score",
    "Layer", "EntityType", "Shape", "UseCase", "RampProfile", "SHAPE_TO_LAYER",
    "DemoConfig", "RegionConfig", "TopologyConfig",
    "default_config", "tiny_config", "CANONICAL_REGIONS",
    "SeededRandom",
    "FROZEN_CONTRACT_VERSION",
    "assert_four_field_boundary", "assert_core_stream_clean",
]
