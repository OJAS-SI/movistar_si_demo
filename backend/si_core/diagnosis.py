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
from typing import List, Optional

from .contracts import Diagnosis, Layer, Shape
from .telemetry import IntervalTelemetry, TelemetryGenerator
from .topology import ServiceGraph


# ---------------------------------------------------------------------------
# The formatted artifacts
# ---------------------------------------------------------------------------

@dataclass
class ReceiptCard:
    """A certified-decision receipt in the external register: a claim, the supporting
    facts (structural plus joined corroboration), an independent cross-check, the
    provenance of the verdict, and a confidence."""
    claim: str
    evidence_lines: List[str]
    check: str
    provenance: str
    confidence: float


@dataclass
class DiagnosisReport:
    """The operator-facing output for one verdict: a one-line recommendation, a
    Structural Health Index band, and the receipt beneath it."""
    timestamp: int
    kind: str                  # "detection" | "abstention" | "all_clear"
    headline: str
    health_band: str
    receipt: Optional[ReceiptCard]
    diagnosis: Optional[Diagnosis] = None

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
        return DiagnosisReport(
            timestamp=t, kind="all_clear",
            headline="All clear: no forming fault across the monitored network.",
            health_band="healthy", receipt=None, diagnosis=None)

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

        if shape == Shape.CLUSTER:
            headline = (f"Access node {entity} ({place}) degrading: {n} homes with rising "
                        f"freeze/re-tune over the past ~{minutes} min, signature local access "
                        f"cluster. Recommended: {d.recommended_action}.")
        elif shape == Shape.SINGLE:
            headline = (f"Household {entity} ({place}) degrading in isolation: rising "
                        f"freeze with weak home connectivity over the past ~{minutes} min, "
                        f"peers on the access node healthy, signature isolated home gateway. "
                        f"Recommended: {d.recommended_action}.")
        elif shape == Shape.PATH:
            headline = (f"Core route {entity} degrading: {n} homes across {n_access} access "
                        f"nodes impaired together over the past ~{minutes} min, signature "
                        f"shared core transport. Recommended: {d.recommended_action}.")
        else:  # SOURCE
            channel = self.graph.nodes[entity].identity.get("channel_name", entity)
            headline = (f"Content source {entity} ({channel}) degrading: {n} homes across "
                        f"{n_access} access nodes watching it impaired over the past "
                        f"~{minutes} min, signature shared content source. "
                        f"Recommended: {d.recommended_action}.")

        receipt = self._receipt(d, corroboration)
        return DiagnosisReport(timestamp=d.timestamp, kind="detection", headline=headline,
                               health_band=band, receipt=receipt, diagnosis=d)

    # ----- abstention -----

    def _format_abstention(self, d: Diagnosis, it: IntervalTelemetry) -> DiagnosisReport:
        tail = d.recommended_action or "insufficient evidence, escalate to human review"
        tail = tail[0].upper() + tail[1:] if tail else tail
        headline = ("Competence boundary: a disturbance is forming but the evidence will "
                    "not yet resolve to a layer. " + tail + ".")
        receipt = self._receipt(d, corroboration=[])
        return DiagnosisReport(timestamp=d.timestamp, kind="abstention", headline=headline,
                               health_band="watch", receipt=receipt, diagnosis=d)

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
        if d.shape == Shape.SINGLE:
            return "degraded for the household"
        if d.confidence >= 0.85 and n_affected >= 3:
            return "critical for the affected element"
        if d.confidence >= 0.6:
            return "degraded for the affected element"
        return "watch"

    def _corroboration(self, entity: str, layer: Layer, shape: Shape,
                       affected: List[str], it: IntervalTelemetry) -> List[str]:
        """Operator-detail facts joined from enrichment, corroborating the verdict.
        Clearly context, not the basis of detection."""
        out: List[str] = []
        rec = it.enrichment.get(entity)
        if shape == Shape.CLUSTER and rec:
            f = rec.fields
            out.append(f"access node port utilization {f.get('port_utilization', 0):.0%}, "
                       f"FEC errors {f.get('fec_errors', 0)} (corroborating context)")
        elif shape == Shape.SINGLE:
            hrec = it.enrichment.get(entity)
            if hrec:
                f = hrec.fields
                out.append(f"home Wi-Fi SNR {f.get('wifi_snr', '?')} dB, WAN packet loss "
                           f"{f.get('wan_packet_loss', '?')}% (corroborating context)")
        elif shape == Shape.SOURCE and rec:
            f = rec.fields
            out.append(f"content segment failures {f.get('segment_failures', 0)}, "
                       f"encoder dropped frames {f.get('encoder_dropped_frm', 0)} "
                       f"(corroborating context)")
        elif shape == Shape.PATH and rec:
            f = rec.fields
            out.append(f"core transport load {f.get('transport_load', 0):.0%}, path latency "
                       f"{f.get('path_latency_ms', '?')} ms (corroborating context)")
        # a sample affected home's freeze, to ground the symptom
        if affected:
            sample = affected[0]
            srec = it.enrichment.get(sample)
            if srec:
                out.append(f"example home {sample} freeze {srec.fields.get('freeze_duration', 0):.1f}s "
                           f"this interval")
        return out

    def _receipt(self, d: Diagnosis, corroboration: List[str]) -> ReceiptCard:
        e = d.evidence
        evidence_lines = list(e.supporting) + corroboration
        p = e.provenance
        n = len(p.entities_examined)
        sample = ", ".join(p.entities_examined[:3])
        shown = f"; signature spans {n} homes (e.g., {sample})" if n else ""
        provenance = (f"derived from the four-field magnitude stream over intervals "
                      f"{p.interval_start} to {p.interval_end}; {p.note}{shown}")
        return ReceiptCard(claim=e.claim, evidence_lines=evidence_lines, check=e.check,
                           provenance=provenance, confidence=d.confidence)
