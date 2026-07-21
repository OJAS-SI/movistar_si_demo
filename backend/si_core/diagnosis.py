"""
Module 5 - Diagnosis and certified-receipt formatter.

This turns the engine's structural verdict into the operator-facing artifact the
specification asks for: a single human-readable recommendation line, and beneath it
a certified-decision receipt that a manager can read and trust. It is where
enrichment legitimately enters, joined to the diagnosis by (entity_id, timestamp),
to colour the line with operator detail. Enrichment was never an input to detection;
it only enriches the explanation.

The operator line follows the form Nodofact specified, for example:
    Access node OLT-2807001-03 (Madrid metro / Las Tablas) degrading: 18 homes with
    rising freeze/re-tune over the past 30 min, signature local access cluster.
    Recommended: inspect the access node and its aggregation before complaints escalate.

An honest abstention renders as a deferral to a human, not a guess.

TWO-REGISTER DISCIPLINE. Everything this module emits is in the EXTERNAL register:
the three coined handles (Structural Health Index, certified-decision receipt,
competence boundary) and plain telecom language. The operator-algebra vocabulary,
the Knowledge Bank, the canonical objects: none of it appears here. The receipt
speaks of homes, access nodes, routes, content sources, departures from baseline,
and a cross-check, nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .contracts import ActionCode, Diagnosis, Layer, Msg, Shape
from .messages import render, render_all
from .telemetry import IntervalTelemetry, TelemetryGenerator
from .topology import ServiceGraph


# ---------------------------------------------------------------------------
# The formatted artifacts
# ---------------------------------------------------------------------------

@dataclass
class ReceiptCard:
    """A certified-decision receipt in the external register: a claim, the supporting
    facts (structural plus joined corroboration), an independent cross-check, the
    provenance of the verdict, and a confidence.

    Every prose leg travels twice: as English, and as the language-free Msg it was
    built from. See DiagnosisReport for why."""
    claim: str
    evidence_lines: List[str]
    check: str
    provenance: str
    confidence: float
    claim_msg: Optional[Msg] = None
    evidence_msgs: List[Msg] = field(default_factory=list)
    check_msg: Optional[Msg] = None
    provenance_msg: Optional[Msg] = None


@dataclass
class DiagnosisReport:
    """The operator-facing output for one verdict: a one-line recommendation, a
    Structural Health Index band, and the receipt beneath it.

    The English fields are what the text console and the HTML export have always
    printed, and they stay. Beside each sits the Msg it was assembled from, so the web
    console can ask for the same sentence in Spanish without this module knowing that
    Spanish exists. The pair is written in one place; they must not drift.
    """
    timestamp: int
    kind: str                  # "detection" | "abstention" | "all_clear"
    headline: str
    health_band: str
    receipt: Optional[ReceiptCard]
    diagnosis: Optional[Diagnosis] = None
    headline_msg: Optional[Msg] = None
    health_band_msg: Optional[Msg] = None

    def render(self) -> str:
        lines = [self.headline, f"Structural Health Index: {self.health_band}"]
        if self.receipt is not None:
            r = self.receipt
            lines.append("Certified-decision receipt:")
            lines.append(f"  Claim: {r.claim}")
            lines.append("  Evidence:")
            lines.extend(f"    - {e}" for e in r.evidence_lines)
            lines.append(f"  Check: {r.check}")
            lines.append(f"  Provenance: {r.provenance}")
            lines.append(f"  Confidence: {r.confidence:.2f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The formatter
# ---------------------------------------------------------------------------

class DiagnosisFormatter:
    """Joins a Diagnosis to the enrichment for its named entity at its interval, and
    produces the operator line and receipt. Construct it with the service graph (for
    the static names and groupings); pass each diagnosis with the interval telemetry
    that carries the enrichment to join."""

    def __init__(self, graph: ServiceGraph) -> None:
        self.graph = graph
        self.interval_seconds = graph.config.interval_seconds
        self.ceiling = TelemetryGenerator.HEALTHY_CEILING

    # ----- public API -----

    def format(self, diagnosis: Diagnosis, telemetry: IntervalTelemetry) -> DiagnosisReport:
        if diagnosis.abstained:
            return self._format_abstention(diagnosis, telemetry)
        if diagnosis.detected:
            return self._format_detection(diagnosis, telemetry)
        return self.all_clear(diagnosis.timestamp)

    def all_clear(self, t: int) -> DiagnosisReport:
        headline_msg, band_msg = Msg("headline.all_clear", {}), Msg("band.healthy", {})
        return DiagnosisReport(
            timestamp=t, kind="all_clear",
            headline=render(headline_msg), health_band=render(band_msg),
            receipt=None, diagnosis=None,
            headline_msg=headline_msg, health_band_msg=band_msg)

    # ----- detection -----

    def _format_detection(self, d: Diagnosis, it: IntervalTelemetry) -> DiagnosisReport:
        entity, layer, shape = d.entity_id, d.layer, d.shape
        minutes = self._window_minutes(d)
        # the affected population is exactly the engine's sustained signature set, so
        # the headline count matches the receipt rather than being recounted
        affected = list(d.evidence.provenance.entities_examined)
        n = len(affected)
        n_access = len({self.graph.stb_membership[h].olt_id
                        for h in affected if h in self.graph.stb_membership}) if affected else 0
        place = self._place(entity, layer)
        band = self._health_band(d, n)
        corroboration = self._corroboration(entity, layer, shape, affected, it)

        # The recommendation is nested rather than interpolated: a catalogue renders the
        # action in the caller's language and drops it into the headline of that same
        # language, so the sentence never ends up half-translated.
        action_msg = Msg(f"action.{d.action_code.value}", {}) if d.action_code else None

        if shape == Shape.CLUSTER:
            headline_msg = Msg("headline.cluster", {"entity": entity, "place": place, "n": n,
                                                    "minutes": minutes, "action": action_msg})
        elif shape == Shape.SINGLE:
            headline_msg = Msg("headline.single", {"entity": entity, "place": place,
                                                   "minutes": minutes, "action": action_msg})
        elif shape == Shape.PATH:
            headline_msg = Msg("headline.path", {"entity": entity, "n": n, "n_access": n_access,
                                                  "minutes": minutes, "action": action_msg})
        else:  # SOURCE
            channel = self.graph.nodes[entity].identity.get("channel_name", entity)
            headline_msg = Msg("headline.source", {"entity": entity, "channel": channel, "n": n,
                                                   "n_access": n_access, "minutes": minutes,
                                                   "action": action_msg})

        receipt = self._receipt(d, corroboration)
        return DiagnosisReport(timestamp=d.timestamp, kind="detection",
                               headline=render(headline_msg),
                               health_band=band, receipt=receipt, diagnosis=d,
                               headline_msg=headline_msg,
                               health_band_msg=self._health_band_msg(d, n))

    # ----- abstention -----

    def _format_abstention(self, d: Diagnosis, it: IntervalTelemetry) -> DiagnosisReport:
        code = d.action_code or ActionCode.ESCALATE_TO_HUMAN
        headline_msg = Msg("headline.abstention",
                           {"action": Msg(f"action.{code.value}", {})})
        band_msg = Msg("band.watch", {})
        receipt = self._receipt(d, corroboration=[])
        return DiagnosisReport(timestamp=d.timestamp, kind="abstention",
                               headline=render(headline_msg),
                               health_band=render(band_msg), receipt=receipt, diagnosis=d,
                               headline_msg=headline_msg, health_band_msg=band_msg)

    # ----- helpers -----

    def _window_minutes(self, d: Diagnosis) -> int:
        p = d.evidence.provenance
        window = max(1, p.interval_end - p.interval_start)
        return max(1, round(window * self.interval_seconds / 60))

    def _place(self, entity: str, layer: Layer) -> str:
        node = self.graph.nodes.get(entity)
        if node is None:
            return "national"
        if layer == Layer.HOME:
            return node.region
        central = node.identity.get("central_office")
        return f"{node.region} / {central}" if central else node.region

    def _health_band(self, d: Diagnosis, n_affected: int) -> str:
        return render(self._health_band_msg(d, n_affected))

    def _health_band_msg(self, d: Diagnosis, n_affected: int) -> Msg:
        return Msg(self._band_key(d, n_affected), {})

    @staticmethod
    def _band_key(d: Diagnosis, n_affected: int) -> str:
        if d.shape == Shape.SINGLE:
            return "band.degraded_household"
        if d.confidence >= 0.85 and n_affected >= 3:
            return "band.critical_element"
        if d.confidence >= 0.6:
            return "band.degraded_element"
        return "band.watch"

    def _corroboration(self, entity: str, layer: Layer, shape: Shape,
                       affected: List[str], it: IntervalTelemetry) -> List[Msg]:
        """Operator-detail facts joined from enrichment, corroborating the verdict.
        Clearly context, not the basis of detection.

        Returned as messages, so one pass over enrichment serves either language."""
        out: List[Msg] = []
        rec = it.enrichment.get(entity)
        if shape == Shape.CLUSTER and rec:
            f = rec.fields
            out.append(Msg("corrob.access_node", {"util": f.get("port_utilization", 0),
                                                  "fec": f.get("fec_errors", 0)}))
        elif shape == Shape.SINGLE:
            hrec = it.enrichment.get(entity)
            if hrec:
                f = hrec.fields
                out.append(Msg("corrob.home", {"snr": f.get("wifi_snr", "?"),
                                               "loss": f.get("wan_packet_loss", "?")}))
        elif shape == Shape.SOURCE and rec:
            f = rec.fields
            out.append(Msg("corrob.content", {"segments": f.get("segment_failures", 0),
                                              "frames": f.get("encoder_dropped_frm", 0)}))
        elif shape == Shape.PATH and rec:
            f = rec.fields
            out.append(Msg("corrob.core", {"load": f.get("transport_load", 0),
                                           "latency": f.get("path_latency_ms", "?")}))
        # a sample affected home's freeze, to ground the symptom
        if affected:
            sample = affected[0]
            srec = it.enrichment.get(sample)
            if srec:
                freeze = srec.fields.get("freeze_duration", 0)
                out.append(Msg("corrob.example_home",
                               {"home": sample, "freeze": round(freeze, 1)}))
        return out

    def _receipt(self, d: Diagnosis, corroboration: List[Msg]) -> ReceiptCard:
        e = d.evidence
        evidence_msgs = list(e.supporting_msgs) + list(corroboration)
        evidence_lines = render_all(evidence_msgs)
        p = e.provenance
        n = len(p.entities_examined)
        sample = ", ".join(p.entities_examined[:3])
        provenance_msg = Msg("provenance.derived", {
            "start": p.interval_start, "end": p.interval_end,
            "note": p.note_msg or Msg("provenance.four_field_only", {}),
            "n": n, "sample": sample})
        return ReceiptCard(claim=e.claim, evidence_lines=evidence_lines, check=e.check,
                           provenance=render(provenance_msg), confidence=d.confidence,
                           claim_msg=e.claim_msg, evidence_msgs=evidence_msgs,
                           check_msg=e.check_msg, provenance_msg=provenance_msg)
