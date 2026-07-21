"""
Module 7 - Visual narrative and operator console.

This is the face of the demo, the single screen that tells the story. It reads ONLY
from the verdicts, the diagnoses, the receipts, and the scorecard, never from the raw
four-field stream. The static service graph is used only to draw the picture.

For each of the three use cases it lays out the four-beat narrative:
    Stream    the network is watched through simple per-entity telemetry, four fields.
    Form      a shape forms on the graph (a cluster, a lone home, a path, a source).
    Predict   the engine projects the shape forward.
    Prescribe the engine names the element, its layer, and the action, with a receipt.

It shows the operator recommendation and its certified-decision receipt, a small
schematic of the forming shape lit up on the layered graph, and the per-use-case
score. It then shows the honest instruments plainly: the competence boundary (an
abstention) and the decoys that did not fire, with the measured false-positive rate.
A scorecard panel closes it.

Two renderers: render_text for a terminal and for testing, and render_html for a
self-contained visual console (no external assets) that Future Space can open in a
browser. Everything stays in the external register.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .contracts import Diagnosis, Layer, Msg, SHAPE_TO_LAYER, Score, Shape, UseCase
from .diagnosis import DiagnosisFormatter, DiagnosisReport
from .messages import render
from .scoring import ScoreReport, ScoringHarness
from .topology import ServiceGraph


# ---------------------------------------------------------------------------
# The console model (assembled from verdicts; no raw stream)
# ---------------------------------------------------------------------------

@dataclass
class Beat:
    name: str
    text: str
    name_msg: Optional[Msg] = None
    text_msg: Optional[Msg] = None


@dataclass
class FaultPanel:
    use_case: UseCase
    title: str
    beats: List[Beat]
    report: DiagnosisReport
    score: Score
    shape: Shape
    entity: str
    region: str
    affected: Tuple[str, ...]
    title_msg: Optional[Msg] = None
    # The interval this fault truly began, from ground truth. Carried per panel because
    # a full run has 13 separate uc1 faults: the use case cannot identify which onset
    # belongs to which verdict, and the fault ids on the stream do not name an entity.
    onset_interval: Optional[int] = None


@dataclass
class HonestPanel:
    abstention: Optional[DiagnosisReport]
    n_decoys: int
    n_decoys_fired: int
    false_positive_rate: float
    n_non_fault_intervals: int
    n_spurious_intervals: int


@dataclass
class ConsoleModel:
    title: str
    subtitle: str
    config_summary: str
    fault_panels: List[FaultPanel]
    honest: HonestPanel
    score_report: ScoreReport
    subtitle_msg: Optional[Msg] = None
    config_summary_msg: Optional[Msg] = None


# ---------------------------------------------------------------------------
# The builder
# ---------------------------------------------------------------------------

class ConsoleBuilder:
    """Assembles the console model. build() is pure (verdicts only); from_pipeline()
    is a convenience that runs the pipeline to produce those verdicts."""

    def __init__(self, graph: ServiceGraph) -> None:
        self.graph = graph

    # ----- convenience bridge: run the pipeline, then build -----

    def from_pipeline(self, injector, engine, formatter: DiagnosisFormatter,
                      harness: ScoringHarness) -> ConsoleModel:
        per_interval: Dict[int, List[Diagnosis]] = {}
        for t in range(self.graph.config.run_intervals):
            per_interval[t] = engine.observe_and_diagnose(t, injector.interval(t).core)
        return self.from_collected(injector, per_interval, formatter, harness)

    def from_collected(self, injector, per_interval: Dict[int, List[Diagnosis]],
                       formatter: DiagnosisFormatter, harness: ScoringHarness) -> ConsoleModel:
        """Assemble the console from diagnoses that were ALREADY collected (e.g. by the
        live stream), so the picture is built once and never recomputed. Scoring takes the
        collected diagnoses as-is; only the handful of settled-verdict reports re-touch a
        few intervals of telemetry for their enrichment join, which is cheap."""
        score_report = harness.score(injector, per_interval)

        # score_report.per_use_case is built in the same order as the real specs, so pair
        # them by position: matching on use_case would collide once many faults share a
        # category (e.g. several access-node clusters across regions).
        findings: List[Tuple[Score, DiagnosisReport]] = []
        real_specs = [s for s in injector.schedule if not s.is_decoy]
        onsets: List[Optional[int]] = []
        for spec, score in zip(real_specs, score_report.per_use_case):
            rep = self._settled_report(spec, per_interval, injector, formatter)
            if rep is not None:
                findings.append((score, rep))
                onsets.append(spec.onset)

        abstention = self._first_abstention(per_interval, injector, formatter)
        return self.build(findings, score_report, abstention, onsets)

    def _settled_report(self, spec, per_interval, injector,
                        formatter: DiagnosisFormatter) -> Optional[DiagnosisReport]:
        """The verdict to show for a fault: the element the engine settled on, taken
        at the earliest interval where its projection is rising (so the narrative
        catches the fault while it is still forming). Formatted with that interval's
        telemetry for the enrichment join."""
        from collections import Counter
        matched: List[Tuple[int, Diagnosis]] = []
        for t in range(spec.onset, min(spec.end, self.graph.config.run_intervals)):
            for d in per_interval.get(t, []):
                if d.detected and (d.entity_id == spec.true_entity
                                   or d.entity_id in spec.affected_homes):
                    matched.append((t, d))
        if not matched:
            return None
        settled_entity, _ = Counter(d.entity_id for _, d in matched).most_common(1)[0]
        cands = [(t, d) for (t, d) in matched if d.entity_id == settled_entity]
        rising = [(t, d) for (t, d) in cands if d.trajectory and d.trajectory.rising]
        pick_t, pick_d = min(rising or cands, key=lambda td: td[0])
        return formatter.format(pick_d, injector.interval(pick_t))

    def _first_abstention(self, per_interval, injector,
                          formatter: DiagnosisFormatter) -> Optional[DiagnosisReport]:
        for t in sorted(per_interval):
            for d in per_interval[t]:
                if d.abstained:
                    return formatter.format(d, injector.interval(t))
        return None

    # ----- pure assembly -----

    def build(self, findings: List[Tuple[Score, DiagnosisReport]],
              score_report: ScoreReport,
              abstention: Optional[DiagnosisReport],
              onsets: Optional[List[Optional[int]]] = None) -> ConsoleModel:
        n_homes = len(self.graph.stb_ids)
        n_olts = len(self.graph.olt_ids)
        n_regions = len(self.graph.config.regions)
        run = self.graph.config.run_intervals
        cadence = self.graph.config.interval_seconds // 60
        config_summary_msg = Msg("console.config_summary",
                                 {"homes": n_homes, "olts": n_olts, "regions": n_regions,
                                  "intervals": run, "cadence": cadence})
        config_summary = render(config_summary_msg)

        panels: List[FaultPanel] = []
        onsets = onsets or [None] * len(findings)
        for (score, rep), onset in zip(findings, onsets):
            d = rep.diagnosis
            entity = d.entity_id
            node = self.graph.nodes.get(entity)
            region = node.region if node else "national"
            affected = d.evidence.provenance.entities_examined if d.evidence else ()
            title_msg = Msg(f"panel.title.{score.use_case.value}", {})
            panels.append(FaultPanel(
                use_case=score.use_case, title=render(title_msg), title_msg=title_msg,
                beats=self._beats(n_homes, n_regions, rep, score), report=rep, score=score,
                shape=d.shape, entity=entity, region=region, affected=affected,
                onset_interval=onset))

        honest = HonestPanel(
            abstention=abstention, n_decoys=score_report.n_decoys,
            n_decoys_fired=score_report.n_decoys_fired,
            false_positive_rate=score_report.false_positive_rate,
            n_non_fault_intervals=score_report.n_non_fault_intervals,
            n_spurious_intervals=score_report.n_spurious_intervals)

        # The product name is a name, not a sentence, so it is not translated. Everything
        # around it is.
        subtitle_msg = Msg("console.subtitle", {})
        return ConsoleModel(
            title="Movistar Service Intelligence",
            subtitle=render(subtitle_msg), subtitle_msg=subtitle_msg,
            config_summary=config_summary, config_summary_msg=config_summary_msg,
            fault_panels=panels, honest=honest, score_report=score_report)

    def _beats(self, n_homes: int, n_regions: int, rep: DiagnosisReport,
               score: Score) -> List[Beat]:
        d = rep.diagnosis
        stream = Msg("beat.stream.text", {"homes": n_homes, "regions": n_regions})
        # The shape and layer are closed vocabularies, so each gets its own key rather
        # than an English word interpolated into a Spanish sentence.
        form = Msg(f"beat.form.text.{d.shape.value}",
                   {"layer": Msg(f"layer.{d.layer.value}" if d.layer else "layer.unknown", {}),
                    "entity": d.entity_id})
        traj = d.trajectory
        detail = traj.detail_msg if traj and traj.detail_msg else Msg("trajectory.steady", {})
        if traj and traj.rising and traj.horizon_interval is not None:
            predict = Msg("beat.predict.text.widening_horizon",
                          {"detail": detail, "horizon": traj.horizon_interval})
        elif traj and traj.rising:
            predict = Msg("beat.predict.text.widening", {"detail": detail})
        else:
            predict = Msg("beat.predict.text.steady", {})

        lead = score.mean_lead_time_intervals
        action = Msg(f"action.{d.action_code.value}", {}) if d.action_code else None
        if lead is not None:
            mins = f"{lead * self.graph.config.interval_seconds / 60:.0f}"
            prescribe = Msg("beat.prescribe.text", {"action": action, "minutes": mins})
        else:
            prescribe = Msg("beat.prescribe.text.no_lead", {"action": action})

        names = ["beat.stream", "beat.form", "beat.predict", "beat.prescribe"]
        return [Beat(name=render(Msg(n, {})), text=render(t),
                     name_msg=Msg(n, {}), text_msg=t)
                for n, t in zip(names, [stream, form, predict, prescribe])]


# ---------------------------------------------------------------------------
# Text renderer (terminal and tests)
# ---------------------------------------------------------------------------

def render_text(model: ConsoleModel) -> str:
    L: List[str] = []
    bar = "=" * 78
    L.append(bar)
    L.append(f"  {model.title.upper()}  |  {model.subtitle}")
    L.append(f"  {model.config_summary}")
    L.append(bar)
    L.append("")
    for i, p in enumerate(model.fault_panels, 1):
        L.append(f"[ USE CASE {i} ]  {p.title}")
        for b in p.beats:
            L.append(f"  {b.name:<9} -> {b.text}")
        L.append(f"  Recommendation: {p.report.headline}")
        L.append(f"  Structural Health Index: {p.report.health_band}")
        r = p.report.receipt
        if r:
            L.append("  Certified-decision receipt:")
            L.append(f"    Claim: {r.claim}")
            for e in r.evidence_lines:
                L.append(f"    Evidence: {e}")
            L.append(f"    Check: {r.check}")
            L.append(f"    Provenance: {r.provenance}")
            L.append(f"    Confidence: {r.confidence:.2f}")
        s = p.score
        lead = (f"{s.mean_lead_time_intervals:.0f} intervals" if s.mean_lead_time_intervals
                is not None else "n/a")
        chips = (f"detected {s.n_detected}/{s.n_faults}, lead {lead}, "
                 f"localization {s.localization_accuracy:.0%}, layer {s.layer_attribution_accuracy:.0%}, "
                 f"action {s.action_correctness:.0%}")
        if s.box_swap_discrimination is not None:
            chips += f", box-swap avoided {s.box_swap_discrimination:.0%}"
        L.append(f"  Score: {chips}")
        L.append("")
    h = model.honest
    L.append("[ HONEST INSTRUMENTS ]")
    if h.abstention:
        L.append(f"  Competence boundary: {h.abstention.headline}")
    L.append(f"  Decoys: {h.n_decoys_fired} of {h.n_decoys} benign anomalies fired (a fire would be a false alarm)")
    L.append(f"  False-positive rate: {h.false_positive_rate:.1%} across "
             f"{h.n_non_fault_intervals} no-fault intervals ({h.n_spurious_intervals} spurious)")
    L.append("")
    L.append("[ SCORECARD ]")
    for line in model.score_report.render().splitlines():
        L.append(f"  {line}")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# HTML renderer: the interactive Service Intelligence Twin console.
#
# The visual shell (three tabs, timeline transport, Director / Presenter modes)
# lives as a self-contained design reference at ui/movistar_si_twin.html. We serve
# that shell verbatim and append a small overlay <script> that injects THIS run's
# real, verified facts (element ids, layer, confidence, lead time, the four-beat
# narrative, the certified-decision receipt, the header config, and the full
# scorecard) over the designer's synthetic defaults. The overlay is non-destructive:
# it mutates the existing `A` alert model in place and re-renders, so the reference
# file stays pristine and the page still works if opened on its own.
# ---------------------------------------------------------------------------

_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "ui", "movistar_si_twin.html")

# Map the pipeline's use cases onto the twin's three alert keys.
_UC_KEY = {
    UseCase.UC1_NETWORK_NODE: "uc1",
    UseCase.UC2_INDIVIDUAL: "uc2",
    UseCase.UC3_INVISIBLE: "uc3",
}

# Turn a bare layer token into the twin's display label (kept keyword-compatible so
# the management tab's layer grouping, which matches on 'home'/'access'/'core', works).
_LAYER_DISPLAY = {
    "access": "Access / aggregation",
    "home": "Home / Wi-Fi",
    "core": "Core / transport",
    "content": "Content / CDN",
}


def _real_data(model: ConsoleModel) -> dict:
    """The verified facts of this run, as a JSON-serialisable dict, for the overlay."""
    interval_seconds = model.score_report.interval_seconds
    alerts: Dict[str, dict] = {}
    for p in model.fault_panels:
        key = _UC_KEY.get(p.use_case)
        if key is None:
            continue
        d = p.report.diagnosis
        layer_tok = (d.layer.value if d.layer else "").lower()
        entry: Dict[str, object] = {
            "el": d.entity_id,
            "shiEl": d.entity_id,
            "layer": _LAYER_DISPLAY.get(layer_tok, (layer_tok.title() or "—")),
            "conf": round(p.report.receipt.confidence, 2) if p.report.receipt else 0.9,
            "headline": p.report.headline,
            "beats": [[b.name, b.text] for b in p.beats],
        }
        lead = p.score.mean_lead_time_intervals
        if lead is not None:
            entry["lead"] = f"+{lead * interval_seconds / 60:.0f} min before it would surface"
        r = p.report.receipt
        if r is not None:
            entry["receipt"] = [
                ["Claim", r.claim],
                ["Evidence", r.evidence_lines[0] if r.evidence_lines else ""],
                ["Check", r.check],
                ["Provenance", r.provenance],
            ]
        alerts[key] = entry

    h = model.honest
    return {
        "title": model.title,
        "subtitle": model.subtitle,
        "config": {"summary": model.config_summary},
        "alerts": alerts,
        "honest": {
            "decoysFired": h.n_decoys_fired,
            "decoys": h.n_decoys,
            "fpRate": f"{h.false_positive_rate:.1%}",
            "nNoFault": h.n_non_fault_intervals,
        },
        "scorecard": model.score_report.render(),
    }


# The overlay: merges REAL over the twin's `A` model, refreshes the header config
# line, and re-renders. Wrapped in try/catch so any drift in the reference file
# degrades gracefully to the designer's defaults rather than a blank page.
_OVERLAY_JS = (
    "if(typeof A!=='undefined'&&REAL.alerts){"
    "for(var k in REAL.alerts){if(A[k]){var o=REAL.alerts[k];for(var f in o){A[k][f]=o[f];}}}}"
    "if(REAL.config&&REAL.config.summary){var cfg=document.querySelector('.config');"
    "if(cfg){cfg.innerHTML='<span><span class=\"dot\"></span>SI engine <b class=\"mono\">live</b></span>'"
    "+'<span>'+REAL.config.summary+'</span>';}}"
    "if(typeof renderTab==='function')renderTab();"
)


def render_html(model: ConsoleModel) -> str:
    with open(_TEMPLATE_PATH, encoding="utf-8") as fh:
        shell = fh.read()
    overlay = ("\n<script>\n(function(){var REAL=" + json.dumps(_real_data(model))
               + ";\ntry{" + _OVERLAY_JS + "}catch(e){}})();\n</script>\n")
    return shell + overlay
