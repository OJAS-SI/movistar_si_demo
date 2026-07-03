"""
Standalone test for Module 8 - Orchestrator and plug-and-play entry point.

    python tests/test_module8_orchestrator.py     (no dependencies)
    pytest tests/test_module8_orchestrator.py

Acceptance criteria (from the roadmap): one call runs the whole pipeline end to end;
the run is deterministic from the seed; it produces the console; the internal
self-test passes; the pipeline is robust across seeds, not just the default; and the
command-line entry point handles its arguments (tiny vs full, seed override, HTML
output, quiet, self-test exit code).
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import traceback

import si_demo.core as c
from si_demo.orchestrator import (
    DemoResult, build_arg_parser, config_for_scale, main, run_demo,
)


# ---------------------------------------------------------------------------
# 1. One call runs the whole pipeline
# ---------------------------------------------------------------------------

def test_run_demo_returns_a_populated_result():
    r = run_demo(c.tiny_config())
    assert isinstance(r, DemoResult)
    assert r.graph is not None and r.score_report is not None
    assert r.console_model is not None
    assert r.text_console and r.html_console
    assert r.html_console.startswith("<!doctype html>")
    assert r.runtime_seconds >= 0
    # the console reflects the three faults
    assert len(r.console_model.fault_panels) == 3


def test_text_and_html_carry_the_narrative():
    r = run_demo(c.tiny_config())
    for beat in ["Stream", "Form", "Predict", "Prescribe"]:
        assert beat in r.text_console
    assert "Certified-decision receipt" in r.text_console
    assert "false-positive rate" in r.text_console
    assert "<svg" in r.html_console


# ---------------------------------------------------------------------------
# 2. Determinism from the seed
# ---------------------------------------------------------------------------

def test_run_is_deterministic_from_the_seed():
    a = run_demo(c.tiny_config(seed=12345))
    b = run_demo(c.tiny_config(seed=12345))
    assert a.text_console == b.text_console
    assert a.html_console == b.html_console


def test_different_seed_changes_the_detail_but_still_passes():
    a = run_demo(c.tiny_config(seed=1))
    b = run_demo(c.tiny_config(seed=2))
    # the named elements differ across topologies
    a_ents = {p.entity for p in a.console_model.fault_panels}
    b_ents = {p.entity for p in b.console_model.fault_panels}
    assert a_ents != b_ents
    assert a.passed() and b.passed()


# ---------------------------------------------------------------------------
# 3. The internal self-test, and robustness across seeds
# ---------------------------------------------------------------------------

def test_self_test_passes_on_default_seed():
    r = run_demo(c.tiny_config())
    assert r.passed() is True


def test_pipeline_is_robust_across_seeds():
    # every random topology should be detected, attributed, and clean
    for seed in [1, 2, 3, 7, 42, 777]:
        r = run_demo(c.tiny_config(seed=seed))
        assert r.passed(), f"self-test failed for seed {seed}"


def test_summary_states_the_key_facts():
    r = run_demo(c.tiny_config())
    s = r.summary()
    assert "faults detected" in s and "false positives" in s
    assert "PASSED" in s


# ---------------------------------------------------------------------------
# 4. Scale selection
# ---------------------------------------------------------------------------

def test_config_for_scale_picks_the_right_size():
    tiny = config_for_scale("tiny")
    full = config_for_scale("full")
    assert tiny.n_stb_target <= 100
    assert full.n_stb_target > 200
    # seed override flows through
    assert config_for_scale("tiny", seed=99).seed == 99
    assert config_for_scale("full", seed=99).seed == 99


# ---------------------------------------------------------------------------
# 5. The command-line entry point
# ---------------------------------------------------------------------------

def _run_main(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


def test_cli_runs_tiny_and_returns_zero():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "console.html")
        code, text = _run_main(["--scale", "tiny", "--out", path, "--quiet"])
        assert code == 0
        assert "Movistar SI demo" in text
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as fh:
            assert fh.read().startswith("<!doctype html>")


def test_cli_self_test_returns_zero_on_success():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "console.html")
        code, text = _run_main(["--scale", "tiny", "--self-test", "--out", path, "--quiet"])
        assert code == 0
        assert "Self-test: PASSED" in text


def test_cli_no_html_does_not_write_a_file():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "console.html")
        code, text = _run_main(["--scale", "tiny", "--no-html", "--out", path, "--quiet"])
        assert code == 0
        assert not os.path.exists(path)


def test_cli_full_console_includes_the_four_beats():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "console.html")
        code, text = _run_main(["--scale", "tiny", "--out", path])
        assert code == 0
        # the non-quiet run prints the text console with the narrative
        assert "Stream" in text and "Prescribe" in text
        assert "SCORECARD" in text


def test_arg_parser_defaults_to_tiny():
    args = build_arg_parser().parse_args([])
    assert args.scale == "tiny" and args.seed is None


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
    print(f"\nModule 8 standalone test: {passed} passed, {failed} failed, {len(tests)} total")
    for name, tb in failures:
        print(f"\n{name}:\n{tb}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
