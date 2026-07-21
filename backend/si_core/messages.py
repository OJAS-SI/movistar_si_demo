"""
The message catalogue: how the domain's statements read in a given language.

WHY THIS EXISTS, AND WHERE IT SITS IN THE LAYERING

Everywhere else, si_core answers "what is true". This file answers "how does that
read", and it answers it for English only - the canonical wording the demo has always
printed, lifted out of the f-strings that used to hold it. Spanish lives in si_api,
because which language a caller wants is a property of the request, not of the network.

That split is deliberate. The text console, the scorecard and the self-contained HTML
export are pure si_core and must keep working with no API in sight, so the domain has
to be able to render its own English. Nothing beyond English belongs here.

HOW A MESSAGE RENDERS

A Msg is a key plus its facts. A catalogue maps the key to a format string, and
`render` fills it in. Two details matter:

  Nested messages. A parameter may itself be a Msg - the headline embeds the
  recommended action this way. It is rendered first, in the SAME catalogue, so a
  sentence can never come out half-translated.

  Missing keys. A gap renders as a visible marker rather than raising, because a demo
  losing one line in front of an audience beats a demo crashing in front of one. Gaps
  are meant to be caught before that: `missing_keys` compares any catalogue against
  this one, and the test suite fails on a difference.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

from .contracts import Msg

# ---------------------------------------------------------------------------
# English - the canonical wording
# ---------------------------------------------------------------------------

CATALOGUE_EN: Dict[str, str] = {
    # ----- what the engine recommends -----
    "action.inspect_access_node":
        "inspect the access node and its aggregation before complaints escalate",
    "action.contact_customer_gateway":
        "proactive customer contact and gateway reconfiguration, no truck roll",
    "action.investigate_core_route":
        "investigate the core transport route carrying the affected homes",
    "action.investigate_content_source":
        "investigate the content source and its delivery path",
    "action.watch_and_confirm":
        "a cluster may be forming on this access node, watch and confirm",
    "action.escalate_to_human":
        "insufficient or ambiguous evidence, escalate to human review",
    "action.swap_set_top_box":
        "swap the set-top box",

    # ----- the operator headline -----
    "headline.cluster":
        "Access node {entity} ({place}) degrading: {n} homes with rising freeze/re-tune "
        "over the past ~{minutes} min, signature local access cluster. "
        "Recommended: {action}.",
    "headline.single":
        "Household {entity} ({place}) degrading in isolation: rising freeze with weak "
        "home connectivity over the past ~{minutes} min, peers on the access node "
        "healthy, signature isolated home gateway. Recommended: {action}.",
    "headline.path":
        "Core route {entity} degrading: {n} homes across {n_access} access nodes "
        "impaired together over the past ~{minutes} min, signature shared core "
        "transport. Recommended: {action}.",
    "headline.source":
        "Content source {entity} ({channel}) degrading: {n} homes across {n_access} "
        "access nodes watching it impaired over the past ~{minutes} min, signature "
        "shared content source. Recommended: {action}.",
    "headline.abstention":
        "Competence boundary: a disturbance is forming but the evidence will not yet "
        "resolve to a layer. {action_cap}.",
    "headline.all_clear":
        "All clear: no forming fault across the monitored network.",

    # ----- the same headlines as a title -----
    # The full sentence is the operator's answer, but it is a paragraph, and a paragraph
    # makes a poor heading: at a glance the reader wants the element and what is wrong
    # with it, with the detail underneath. Same key stem plus ".short", so the two can
    # never name different faults.
    "headline.short.cluster": "Access node {entity} degrading",
    "headline.short.single": "Household {entity} declining",
    "headline.short.path": "Core route {entity} degrading",
    "headline.short.source": "Content source {entity} degrading",
    "headline.short.abstention": "Competence boundary",
    "headline.short.all_clear": "All clear",

    # ----- the Structural Health Index bands -----
    "band.degraded_household": "degraded for the household",
    "band.critical_element": "critical for the affected element",
    "band.degraded_element": "degraded for the affected element",
    "band.watch": "watch",
    "band.healthy": "healthy",

    # The band as a pill. The long form is a phrase that completes "Structural Health
    # Index: ..."; on a badge it only needs the word.
    "band.short.degraded_household": "Degraded",
    "band.short.critical_element": "Critical",
    "band.short.degraded_element": "Degraded",
    "band.short.watch": "Watch",
    "band.short.healthy": "Healthy",

    # ----- the certified-decision receipt -----
    "receipt.claim.cluster":
        "Access node {entity} degrading: {n} homes behind it with rising impairment",
    "receipt.claim.single":
        "Household {entity} degrading in isolation; its access-node peers are healthy",
    "receipt.claim.path":
        "Core route {entity} degrading: homes across several access nodes impaired together",
    "receipt.claim.source":
        "Content source {entity} degrading: otherwise-unrelated homes impaired together",
    "receipt.claim.abstain":
        "A disturbance is forming but the evidence will not yet resolve to a layer",

    "receipt.check.cluster":
        "the elevated homes share one access node and their other subsystems are within "
        "baseline, inconsistent with a content or core fault",
    "receipt.check.single":
        "only this home is elevated while its node peers remain at baseline, "
        "inconsistent with a shared network fault",
    "receipt.check.path":
        "the elevated homes span multiple access nodes but share one core route, "
        "inconsistent with a single-node or content fault",
    "receipt.check.source":
        "the elevated homes span many access nodes but share one content source, "
        "inconsistent with an access-node fault",
    "receipt.check.abstain":
        "the structural signature is not yet strong or clean enough to attribute",

    "receipt.support.elevated_sustained":
        "{n} homes elevated and sustained beyond the dwell threshold",
    "receipt.support.elevated_sustained.one":
        "1 home elevated and sustained beyond the dwell threshold",
    "receipt.support.mean_departure":
        "mean departure {sigma} standard deviations above the learned baseline",
    "receipt.support.behind_node":
        "{n_behind} of {n} elevated homes sit behind {dst} by the network map",
    "receipt.support.behind_node.one":
        "{n_behind} of 1 elevated home sits behind {dst} by the network map",
    "receipt.support.elevated_near":
        "{n} homes elevated near {dst}",
    "receipt.support.elevated_near.one":
        "1 home elevated near {dst}",
    "receipt.support.convergence_weak":
        "convergence weak or ambiguous; confidence below the action threshold",

    # ----- corroboration joined from enrichment (context, never the basis) -----
    "corrob.access_node":
        "access node port utilization {util:.0%}, FEC errors {fec} (corroborating context)",
    "corrob.home":
        "home Wi-Fi SNR {snr} dB, WAN packet loss {loss}% (corroborating context)",
    "corrob.content":
        "content segment failures {segments}, encoder dropped frames {frames} "
        "(corroborating context)",
    "corrob.core":
        "core transport load {load:.0%}, path latency {latency} ms (corroborating context)",
    "corrob.example_home":
        "example home {home} freeze {freeze}s this interval",

    # ----- provenance -----
    "provenance.four_field_only":
        "four-field magnitude stream only; baselines learned from history",
    "provenance.competence_boundary":
        "competence boundary reached; deferring to human",
    "provenance.derived":
        "derived from the four-field magnitude stream over intervals {start} to {end}; "
        "{note}{signature}",
    "provenance.signature_spans":
        "; signature spans {n} homes (e.g., {sample})",
    "provenance.signature_spans.one":
        "; signature spans 1 home ({sample})",

    # ----- the console frame -----
    "console.subtitle":
        "powered by Structural Intelligence  |  synthetic demo, no Telefonica data",
    "console.config_summary":
        "{homes} homes, {olts} access nodes, {regions} regions, {intervals} intervals at "
        "{cadence} min cadence",

    # ----- what each use case is here to show -----
    "panel.title.uc1_network_node": "A network node degrading (gradual access fault)",
    "panel.title.uc2_individual": "An individual household degrading (isolated, peers healthy)",
    "panel.title.uc3_invisible": "An invisible fault that survives a set-top-box swap",
    "panel.title.uc4_core_path": "A core-transport route degrading (a path across access nodes)",
    "panel.title.uc5_content_source": "A content source degrading (unrelated homes, one source)",

    # ----- the layers, as words in a sentence -----
    "layer.home": "home",
    "layer.access": "access",
    "layer.core": "core",
    "layer.content": "content",
    "layer.unknown": "unknown",

    # ----- the four beats -----
    "beat.stream": "Stream",
    "beat.form": "Form",
    "beat.predict": "Predict",
    "beat.prescribe": "Prescribe",
    "beat.stream.text":
        "{homes} homes across {regions} regions stream four-field telemetry; the engine "
        "learns normal and watches the graph for structure.",
    "beat.form.text.cluster":
        "A cluster forms on the {layer} layer: cluster signature on {entity}.",
    "beat.form.text.single":
        "A single home forms on the {layer} layer: single signature on {entity}.",
    "beat.form.text.path":
        "A path forms on the {layer} layer: path signature on {entity}.",
    "beat.form.text.source":
        "A source forms on the {layer} layer: source signature on {entity}.",
    "beat.form.text.none":
        "A shape forms on the {layer} layer, on {entity}.",
    "beat.predict.text.widening_horizon":
        "Projected to widen ({detail}); on the current trend it would broaden around "
        "interval {horizon} if untreated.",
    "beat.predict.text.widening": "Projected to widen ({detail}).",
    "beat.predict.text.steady": "Projected steady; the engine keeps watching for change.",
    "beat.prescribe.text":
        "{action_cap}. Flagged {minutes} min before the fault would surface; see the "
        "certified-decision receipt.",
    "beat.prescribe.text.no_lead":
        "{action_cap}. See the certified-decision receipt.",

    # ----- the scorecard, rendered as plain text -----
    "scorecard.heading":
        "Structural Intelligence demo scorecard (measured values, no preset thresholds)",
    "scorecard.detected": "detected: {n}/{total}",
    "scorecard.lead_time":
        "detection lead time: {intervals} intervals ({minutes}) before the fault would surface",
    "scorecard.localization": "localization accuracy: {pct}",
    "scorecard.layer_attribution": "layer attribution: {pct}",
    "scorecard.box_swap":
        "box-swap discrimination: {pct} (the box swap would have been avoided)",
    "scorecard.action_correctness": "action correctness: {pct}",
    "scorecard.note": "note: {note}",
    "scorecard.false_positive_rate":
        "false-positive rate: {pct} ({spurious} spurious of {total} no-fault intervals)",
    "scorecard.decoys_fired": "decoys that fired: {fired}/{total}",
    "score.note.not_detected": "not detected",
    "score.note.detected":
        "detected at interval {interval}, named {entity} ({layer}/{shape}), lead {lead} "
        "intervals to surfacing at {surfacing}",

    # ----- the forward projection -----
    "trajectory.widening": "convergence widening",
    "trajectory.steady": "convergence steady",
}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render(msg: Msg, catalogue: Mapping[str, str] = CATALOGUE_EN) -> str:
    """One message, in the wording of one catalogue.

    Nested Msg parameters are rendered in the same catalogue first, so an embedded
    recommendation cannot arrive in a different language from the sentence holding it.
    """
    # Singular agreement. A catalogue may add "<key>.one" for the n == 1 wording; both
    # languages need it ("1 homes elevated", "1 hogares elevados") and Spanish needs it
    # more visibly, since the adjective agrees too.
    key = msg.key
    if msg.params.get("n") == 1 and f"{key}.one" in catalogue:
        key = f"{key}.one"

    template = catalogue.get(key)
    if template is None:
        # Loud but survivable: the demo keeps running and the gap is obvious on screen.
        return f"[{msg.key}]"

    resolved: Dict[str, Any] = {}
    for name, value in msg.params.items():
        rendered = render(value, catalogue) if isinstance(value, Msg) else value
        resolved[name] = rendered
        # A fragment written to sit mid-sentence sometimes has to open one - the
        # abstention headline ends with the recommendation as its own sentence. Offering
        # a capitalised twin keeps that a property of the template, not of the domain,
        # and it works the same way in every language the demo renders.
        if isinstance(rendered, str) and rendered:
            resolved[f"{name}_cap"] = rendered[0].upper() + rendered[1:]

    # `provenance.derived` carries an optional tail; absent means an empty string rather
    # than a missing key, so the template can name it unconditionally.
    if key == "provenance.derived":
        n = resolved.get("n") or 0
        resolved["signature"] = render(
            Msg("provenance.signature_spans",
                {"n": n, "sample": resolved.get("sample", "")}), catalogue) if n else ""

    try:
        return template.format(**resolved)
    except (KeyError, IndexError, ValueError):
        # A template asking for a fact this message does not carry. Show the wording
        # rather than dropping the line entirely.
        return template


def render_all(msgs: Iterable[Msg], catalogue: Mapping[str, str] = CATALOGUE_EN) -> List[str]:
    return [render(m, catalogue) for m in msgs]


def missing_keys(catalogue: Mapping[str, str]) -> List[str]:
    """Keys English defines that this catalogue does not. The test suite asserts this
    is empty for every language the demo ships, so a half-translated console is caught
    in CI rather than on stage."""
    return sorted(k for k in CATALOGUE_EN if k not in catalogue)
