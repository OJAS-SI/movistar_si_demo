"""
Module 9 - the message catalogue and the bilingual boundary.

Two things are worth testing here, and they are the two ways a translated demo goes
wrong without anyone noticing.

THE REGISTERS MUST NOT DRIFT. Every operator sentence exists twice: as the English the
demo has always printed, and as the Msg a catalogue renders. If those diverge, the web
console and the text console start telling different stories about the same run. The
parity test renders every Msg a real run produces and demands it equal its English
twin, character for character.

SCORING MUST NOT READ WORDS. Box-swap discrimination once asked whether the
recommendation contained the substring "box". That measured the language the demo
happened to be written in: translate the recommendation and the check passes on every
input while proving nothing, and the scorecard still reports a number. Scoring now
reads ActionCode, and these tests hold it there.
"""

from __future__ import annotations

import sys
import traceback

import si_core.contracts as c
from si_core.messages import CATALOGUE_EN, missing_keys, render, render_all
from si_core.orchestrator import config_for_scale, run_demo
from si_core.scoring import ScoringHarness


def _reports(result):
    """Every DiagnosisReport a run produced, including the honest abstention."""
    out = [p.report for p in result.console_model.fault_panels]
    if result.console_model.honest.abstention is not None:
        out.append(result.console_model.honest.abstention)
    return out


def _pairs(report):
    """(label, english, msg) for every translatable string on one report."""
    out = [("headline", report.headline, report.headline_msg),
           ("health_band", report.health_band, report.health_band_msg)]
    receipt = report.receipt
    if receipt is not None:
        out += [("claim", receipt.claim, receipt.claim_msg),
                ("check", receipt.check, receipt.check_msg),
                ("provenance", receipt.provenance, receipt.provenance_msg)]
        out += [("evidence", eng, msg)
                for eng, msg in zip(receipt.evidence_lines, receipt.evidence_msgs)]
    return [(label, eng, msg) for label, eng, msg in out if msg is not None]


# ---------------------------------------------------------------------------
# 1. The English catalogue reproduces the English exactly
# ---------------------------------------------------------------------------

def test_english_catalogue_reproduces_every_operator_string():
    """The catalogue was lifted out of the f-strings that used to hold this wording.
    If a lift dropped a word, a number format or a piece of punctuation, this catches
    it on the real output of a real run rather than on a hand-written example."""
    checked = 0
    for seed in (7, 42, 101):
        result = run_demo(config_for_scale("tiny", seed))
        for report in _reports(result):
            for label, english, msg in _pairs(report):
                assert render(msg) == english, (
                    f"seed {seed}, {label}: catalogue and English have drifted\n"
                    f"  english : {english}\n"
                    f"  rendered: {render(msg)}")
                checked += 1
    # guard against the assertions silently never running
    assert checked > 50, f"expected the run to produce many strings, saw {checked}"


def test_nested_messages_render_in_one_language():
    """The headline embeds the recommendation. It must be rendered in the catalogue
    holding the headline, or a sentence arrives half-translated."""
    catalogue = dict(CATALOGUE_EN)
    catalogue["headline.abstention"] = "OUTER {action_cap}."
    catalogue["action.escalate_to_human"] = "inner text"
    msg = c.Msg("headline.abstention",
                {"action": c.Msg("action.escalate_to_human", {})})
    assert render(msg, catalogue) == "OUTER Inner text."


def test_a_missing_key_is_visible_not_fatal():
    """A gap must not take the demo down mid-presentation, and must not pass silently
    for the operator either."""
    assert render(c.Msg("no.such.key", {})) == "[no.such.key]"


def test_missing_keys_reports_the_gap_between_catalogues():
    partial = {k: v for k, v in CATALOGUE_EN.items() if not k.startswith("band.")}
    gaps = missing_keys(partial)
    assert gaps, "a catalogue missing every band key should report gaps"
    assert all(k.startswith("band.") for k in gaps)
    assert missing_keys(CATALOGUE_EN) == []


def test_render_all_maps_a_sequence():
    out = render_all([c.Msg("band.watch", {}), c.Msg("band.healthy", {})])
    assert out == ["watch", "healthy"]


# ---------------------------------------------------------------------------
# 2. Scoring reads the decision, not the wording
# ---------------------------------------------------------------------------

def test_every_detection_carries_an_action_code():
    """Scoring depends on it, so a detection without one would score against None."""
    result = run_demo(config_for_scale("tiny", 7))
    seen = 0
    for report in _reports(result):
        diagnosis = report.diagnosis
        if diagnosis is not None and diagnosis.detected:
            assert diagnosis.action_code is not None, "a detection carried no ActionCode"
            assert isinstance(diagnosis.action_code, c.ActionCode)
            seen += 1
    assert seen > 0, "the run produced no detections to check"


def test_box_swap_check_is_language_independent():
    """The regression this whole refactor exists to prevent. A substring check for
    "box" passes on any Spanish recommendation, so it would have reported perfect
    box-swap discrimination while testing nothing at all."""
    ok = ScoringHarness._action_ok
    assert ok(c.Shape.CLUSTER, c.Layer.ACCESS, c.ActionCode.SWAP_SET_TOP_BOX) is False
    assert ok(c.Shape.CLUSTER, c.Layer.ACCESS, c.ActionCode.INSPECT_ACCESS_NODE) is True

    # the property scoring actually consults, independent of any catalogue
    assert c.ActionCode.SWAP_SET_TOP_BOX.is_box_swap is True
    assert c.ActionCode.INSPECT_ACCESS_NODE.is_box_swap is False

    # and the Spanish wording that would have defeated the old check
    spanish_box_swap = "sustituir el descodificador del cliente"
    assert "box" not in spanish_box_swap.lower()


def test_every_action_code_has_wording():
    """A code with no catalogue entry renders as a marker in the operator's face."""
    for code in c.ActionCode:
        assert f"action.{code.value}" in CATALOGUE_EN, f"no wording for {code}"


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
    print(f"\nModule 9 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
