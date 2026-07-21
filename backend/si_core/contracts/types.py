"""
Module 0 - Shared Foundations: the frozen data contracts.

This file defines the vocabulary every other module imports. It is built first
and frozen, so that Modules 1 through 8 can be developed against stable
interfaces. Nothing in this file performs behaviour; it defines the shapes of
the data that flow through the pipeline.

THE CARDINAL CONTRACT (the four-field boundary):
    The Structural Intelligence engine consumes ONLY CoreRecord, which carries
    exactly four fields: entity_src, entity_dst, timestamp, magnitude. All other
    information travels on EnrichmentRecord and is joined back to SI output only
    at the reporting stage, by the key (entity_id, timestamp). CoreRecord is a
    frozen, slotted dataclass, so it is structurally impossible for enrichment to
    ride along on the channel the SI engine reads. This separation is what proves
    that Structural Intelligence needs only four fields while the demo still looks
    like real operator data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


# =====================================================================
# MESSAGES - what the domain says, before anyone chooses a language
# =====================================================================

@dataclass(frozen=True, slots=True)
class Msg:
    """One thing the domain has to say, as a key and its facts - never as a sentence.

    The demo is bilingual, and the operator-facing prose is assembled from live values
    (entity ids, counts, regions, minutes). Translating finished sentences is hopeless,
    so the domain stops producing them: it produces a key naming what it wants to say
    and the values to say it with. A catalogue turns that into English or Spanish.

    This keeps the layering the rest of the codebase already states. si_core decides
    WHAT is true; a catalogue decides HOW it reads; si_api decides WHICH language the
    caller asked for. The domain never imports a language.

    `params` holds only primitives, so a Msg stays as serialisable as the records
    around it, and a catalogue can format it without reaching back into the domain.
    """
    key: str
    params: Dict[str, Any] = field(default_factory=dict)

    def with_params(self, **extra: Any) -> "Msg":
        """A copy carrying additional facts, for the rare caller that learns one late."""
        merged = dict(self.params)
        merged.update(extra)
        return Msg(key=self.key, params=merged)


# =====================================================================
# ENUMERATIONS - the closed vocabularies of the domain
# =====================================================================

class Layer(str, Enum):
    """The true causal layer a fault can live in. These are the four layers the
    demo must distinguish, and the targets of layer-attribution scoring."""
    HOME = "home"
    ACCESS = "access"
    CORE = "core"
    CONTENT = "content"


class EntityType(str, Enum):
    """The node types in the Telefonica-style GPON/FTTH hierarchy, in path order:
    STB to ONT to OLT to aggregation switch to BNG to core to CDN edge to content."""
    STB = "stb"                 # set-top box
    ONT = "ont"                 # optical network terminal (the home optical endpoint)
    OLT = "olt"                 # optical line terminal in a central office
    AGG = "agg"                 # aggregation switch
    BNG = "bng"                 # broadband network gateway
    CORE = "core"               # core / transport
    CDN_EDGE = "cdn_edge"       # content-distribution edge
    CONTENT = "content"         # content source / encoder


class Shape(str, Enum):
    """The geometric signature a fault makes on the graph. Reading which shape is
    forming, and where, is how SI places a fault in its true layer."""
    SINGLE = "single"           # one affected node, alone -> home
    CLUSTER = "cluster"         # a cluster of homes behind one node -> access
    PATH = "path"               # affected nodes strung along a path -> core
    SOURCE = "source"           # one source impairing many unrelated nodes -> content
    NONE = "none"               # no fault shape present (healthy / decoy)


class ActionCode(str, Enum):
    """What the engine recommends, as a code rather than a sentence.

    This exists because the recommendation has two audiences that must not share a
    representation. The operator reads a sentence, and that sentence has to be
    translatable. The scoring harness reads a decision, and it must keep meaning the
    same thing in every language: scoring once asked whether the string contained the
    word "box" to prove an access fault was never answered with a set-top-box swap,
    which would have silently passed the moment the demo spoke Spanish. The code is
    what scoring reads; the sentence is what the catalogues render.
    """
    INSPECT_ACCESS_NODE = "inspect_access_node"
    CONTACT_CUSTOMER_GATEWAY = "contact_customer_gateway"
    INVESTIGATE_CORE_ROUTE = "investigate_core_route"
    INVESTIGATE_CONTENT_SOURCE = "investigate_content_source"
    WATCH_AND_CONFIRM = "watch_and_confirm"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    SWAP_SET_TOP_BOX = "swap_set_top_box"

    @property
    def is_box_swap(self) -> bool:
        """The futile action the demo exists to avoid. Scoring asks this, not the text."""
        return self is ActionCode.SWAP_SET_TOP_BOX


class UseCase(str, Enum):
    """The injected scenario classes. UC1/UC2/UC3 are the three scripted anchor use
    cases the demo narrative rests on; UC4/UC5 are the core-transport and content-source
    variants generated at full scale so every layer and shape is exercised across all
    regions. DECOY and HEALTHY are the honesty instruments that must NOT trigger a
    fault, and that let the demo measure false positives."""
    UC1_NETWORK_NODE = "uc1_network_node"        # gradual access-node degradation
    UC2_INDIVIDUAL = "uc2_individual"            # isolated per-household decline
    UC3_INVISIBLE = "uc3_invisible"              # label-less fault surviving a box swap
    UC4_CORE_PATH = "uc4_core_path"              # core/transport route degradation (path)
    UC5_CONTENT_SOURCE = "uc5_content_source"    # content source / encoder degradation
    DECOY = "decoy"                              # benign anomaly that must not fire
    HEALTHY = "healthy"                          # long healthy stretch


class RampProfile(str, Enum):
    """How a fault's magnitude rises once injected."""
    SUDDEN = "sudden"
    GRADUAL = "gradual"


# The canonical mapping from a fault shape to the layer it implies. Held here as
# part of the shared contract so every module reasons about it identically.
SHAPE_TO_LAYER: Dict[Shape, Optional[Layer]] = {
    Shape.SINGLE: Layer.HOME,
    Shape.CLUSTER: Layer.ACCESS,
    Shape.PATH: Layer.CORE,
    Shape.SOURCE: Layer.CONTENT,
    Shape.NONE: None,
}


# =====================================================================
# THE CORE RECORD - the ONLY thing the SI engine consumes
# =====================================================================

# The exact, ordered field names of the core record. This tuple is the canonical
# statement of the four-field boundary; the standalone test asserts that the
# CoreRecord dataclass matches it exactly, so the boundary cannot drift.
CORE_RECORD_FIELDS: Tuple[str, ...] = ("entity_src", "entity_dst", "timestamp", "magnitude")


@dataclass(frozen=True, slots=True)
class CoreRecord:
    """One observation, reduced to the four fields Structural Intelligence reads.

    entity_src : the source entity (who emitted this) - also the enrichment join key
    entity_dst : the parent in the path (so the pair defines a directed edge)
    timestamp  : the interval index this observation belongs to
    magnitude  : the sampled signal, the weight on the edge

    frozen=True makes it immutable; slots=True makes it structurally impossible to
    attach any further attribute (e.g. rec.firmware = ... raises AttributeError).
    Together these enforce the four-field boundary at the level of the type itself.
    """
    entity_src: str
    entity_dst: str
    timestamp: int
    magnitude: float

    def __post_init__(self) -> None:
        # Light validation so malformed records fail loudly at the boundary.
        if not isinstance(self.entity_src, str) or not self.entity_src:
            raise ValueError("CoreRecord.entity_src must be a non-empty string")
        if not isinstance(self.entity_dst, str) or not self.entity_dst:
            raise ValueError("CoreRecord.entity_dst must be a non-empty string")
        if not isinstance(self.timestamp, int) or isinstance(self.timestamp, bool):
            raise ValueError("CoreRecord.timestamp must be an int interval index")
        if not isinstance(self.magnitude, (int, float)) or isinstance(self.magnitude, bool):
            raise ValueError("CoreRecord.magnitude must be a real number")

    @property
    def join_key(self) -> Tuple[str, int]:
        """The key (entity_id, timestamp) used to join enrichment at report time.
        The emitting entity is entity_src."""
        return (self.entity_src, self.timestamp)


def make_core_record(entity_src: str, entity_dst: str, timestamp: int,
                     magnitude: float) -> CoreRecord:
    """The sanctioned constructor for a core record. Taking exactly four arguments,
    it is the only documented way to mint one, which keeps the boundary visible at
    every call site."""
    return CoreRecord(entity_src=entity_src, entity_dst=entity_dst,
                      timestamp=int(timestamp), magnitude=float(magnitude))


# =====================================================================
# THE ENRICHMENT RECORD - everything else, joined only at report time
# =====================================================================

@dataclass(frozen=True, slots=True)
class EnrichmentRecord:
    """The full per-entity, per-interval context that gives the demo its colour.

    It carries the join key (entity_id, timestamp) plus the entity's place in the
    hierarchy and a free-form `fields` map holding the identity, flow, and
    enrichment values specified per layer in the data dictionary (firmware_version,
    multicast_group_id, optical_rx_power, and so on).

    CRITICAL: no module upstream of or inside the SI engine may read this type. It
    exists solely to power the operator-facing diagnosis, the visual narrative, and
    the scoring labels. It is joined to SI output by (entity_id, timestamp).
    """
    entity_id: str
    timestamp: int
    entity_type: EntityType
    layer: Layer
    fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def join_key(self) -> Tuple[str, int]:
        return (self.entity_id, self.timestamp)


# =====================================================================
# DIAGNOSIS, EVIDENCE, RECEIPT - the explainable SI output
# =====================================================================

@dataclass(frozen=True, slots=True)
class Provenance:
    """What a diagnosis rested on: the data window and the entities examined. The
    provenance leg of the certified-decision receipt."""
    interval_start: int
    interval_end: int
    entities_examined: Tuple[str, ...]
    note: str = ""
    note_msg: Optional[Msg] = None


@dataclass(frozen=True, slots=True)
class Evidence:
    """The certified-decision receipt material: a claim, the supporting evidence,
    an independent check that re-derives it, and the provenance. This is how every
    diagnosis is made explainable rather than a bare score.

    Each leg exists twice: as the English the demo has always emitted, and as a Msg
    carrying the same fact without a language. The strings keep the text console and
    the HTML export working unchanged; the messages are what a catalogue renders when
    the operator asked for Spanish. They are written together and must not drift.
    """
    claim: str
    supporting: Tuple[str, ...]
    check: str
    provenance: Provenance
    claim_msg: Optional[Msg] = None
    supporting_msgs: Tuple[Msg, ...] = ()
    check_msg: Optional[Msg] = None


@dataclass(frozen=True, slots=True)
class PredictedTrajectory:
    """The forward projection of a forming shape: whether it is rising, and the
    interval at which it is expected to cross into impact (the complaint wave for a
    node, or churn-risk for a household)."""
    rising: bool
    horizon_interval: Optional[int]
    detail: str = ""
    detail_msg: Optional[Msg] = None


@dataclass(frozen=True, slots=True)
class Diagnosis:
    """The SI engine's output for one interval. It speaks only in the external
    register: a named entity, a layer, a shape, a forward projection, a confidence,
    and the evidence. It carries no operator-algebra internals.

    `detected` is True when SI raises a fault this interval. `abstained` is True
    when SI declines because the evidence is insufficient - the honest competence
    boundary - in which case entity_id and layer may be None.
    """
    timestamp: int
    detected: bool
    abstained: bool
    entity_id: Optional[str]
    layer: Optional[Layer]
    shape: Shape
    confidence: float
    trajectory: Optional[PredictedTrajectory]
    evidence: Optional[Evidence]
    recommended_action: Optional[str] = None
    # What the recommendation IS, as opposed to how it reads. Scoring must consult this
    # and never the sentence, or a translated demo would score its own wording.
    action_code: Optional[ActionCode] = None

    def __post_init__(self) -> None:
        if not (0.0 <= float(self.confidence) <= 1.0):
            raise ValueError("Diagnosis.confidence must lie in [0, 1]")
        if self.detected and self.abstained:
            raise ValueError("A diagnosis cannot be both detected and abstained")


# =====================================================================
# GROUND TRUTH - the answer key produced by construction
# =====================================================================

@dataclass(frozen=True, slots=True)
class GroundTruthLabel:
    """The recorded truth of one injected event, the answer key the scoring harness
    compares against. Produced by the fault-injection engine (Module 3) at the
    moment of injection, so the demo has ground truth by construction.

    For a decoy or a healthy stretch, `is_decoy` is True and `true_layer` is None:
    SI must NOT raise a fault, and doing so counts as a false positive.
    """
    fault_id: str
    use_case: UseCase
    onset_time: int
    affected_entities: Tuple[str, ...]
    true_entity: Optional[str]          # the element SI should name
    true_layer: Optional[Layer]         # the layer SI should attribute to
    ramp: RampProfile
    magnitude: float
    is_decoy: bool = False
    has_explicit_error_code: bool = True
    box_swap_time: Optional[int] = None       # UC3: when the simulated swap happens
    tipping_point_time: Optional[int] = None  # UC2: when the household crosses to churn-risk
    recommended_action: Optional[str] = None  # the action that matches this root cause


# =====================================================================
# SCORE - measured against ground truth, never pre-committed
# =====================================================================

@dataclass(frozen=True, slots=True)
class Score:
    """The measured outcome for one use case (or overall, when use_case is None).

    Honouring the specification, this carries measured values only; no numeric
    success threshold is fixed here. Every figure originates from the scoring
    harness comparing diagnoses to ground truth - the witness discipline in code.
    """
    use_case: Optional[UseCase]
    n_faults: int
    n_detected: int
    mean_lead_time_intervals: Optional[float]
    localization_accuracy: Optional[float]
    layer_attribution_accuracy: Optional[float]
    box_swap_discrimination: Optional[float]
    false_positive_rate: Optional[float]
    action_correctness: Optional[float]
    note: str = ""
    note_msg: Optional[Msg] = None
