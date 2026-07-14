"""
Module 8 - Orchestrator and plug-and-play entry point.

This wires the whole pipeline in data-flow order behind a single call, deterministic
from one seed. It is the keystone: one command runs the entire demo end to end.

The data flow, in order:
    build_service_graph        the static Spain-grounded network and its identifiers
      -> FaultInjector         healthy telemetry, perturbed by the scheduled faults,
                               with the ground-truth answer key (wraps the telemetry
                               generator)
      -> StructuralIntelligenceEngine  reads only the four-field stream, on the known
                               network map, and emits diagnoses
      -> DiagnosisFormatter    joins enrichment at report time, produces the operator
                               line and the certified-decision receipt
      -> ScoringHarness        scores every diagnosis against ground truth
      -> ConsoleBuilder        assembles the four-beat narrative and the honest panels
      -> render_text / render_html   the operator console

Two scales, one seed: the tiny configuration for a fast live run, the full
configuration for the production picture. The same seed always reproduces the same
graph, the same faults, the same verdicts, and the same console.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Optional

from .contracts import DemoConfig, UseCase, default_config, tiny_config
from .console import ConsoleBuilder, ConsoleModel, render_html, render_text
from .diagnosis import DiagnosisFormatter
from .fault_injection import FaultInjector
from .scoring import ScoreReport, ScoringHarness
from .si_engine import NetworkMap, StructuralIntelligenceEngine
from .topology import ServiceGraph, build_service_graph


# ---------------------------------------------------------------------------
# The result of a full run
# ---------------------------------------------------------------------------

@dataclass
class DemoResult:
    """Everything one demo run produces, ready to print, write, or inspect."""
    config: DemoConfig
    graph: ServiceGraph
    score_report: ScoreReport
    console_model: ConsoleModel
    text_console: str
    html_console: str
    runtime_seconds: float

    def passed(self) -> bool:
        """The internal self-test: every fault detected and correctly attributed, the
        box swap avoided for the invisible fault, and no false positives. This is the
        one-line health check a presenter can trust before going live."""
        sr = self.score_report
        for s in sr.per_use_case:
            if s.n_detected != 1 or s.localization_accuracy != 1.0 \
                    or s.layer_attribution_accuracy != 1.0 or s.action_correctness != 1.0:
                return False
            if s.use_case == UseCase.UC3_INVISIBLE and s.box_swap_discrimination != 1.0:
                return False
        return sr.false_positive_rate == 0.0 and sr.n_decoys_fired == 0

    def summary(self) -> str:
        sr = self.score_report
        n_det = sum(s.n_detected for s in sr.per_use_case)
        n_tot = sum(s.n_faults for s in sr.per_use_case)
        loc = sum(s.localization_accuracy for s in sr.per_use_case) / max(len(sr.per_use_case), 1)
        lay = sum(s.layer_attribution_accuracy for s in sr.per_use_case) / max(len(sr.per_use_case), 1)
        scale = "full" if len(self.config.regions) >= 6 and self.config.n_stb_target > 200 else "tiny"
        return (f"Movistar SI demo ({scale}, seed {self.config.seed}): "
                f"{n_det}/{n_tot} faults detected, localization {loc:.0%}, layer {lay:.0%}, "
                f"box swap avoided, {sr.false_positive_rate:.1%} false positives across "
                f"{sr.n_non_fault_intervals} no-fault intervals. "
                f"Self-test {'PASSED' if self.passed() else 'FAILED'}. "
                f"Ran {self.config.run_intervals} intervals over {len(self.graph.stb_ids)} homes "
                f"in {self.runtime_seconds:.1f}s.")


# ---------------------------------------------------------------------------
# The single-call pipeline
# ---------------------------------------------------------------------------

def run_demo(config: Optional[DemoConfig] = None) -> DemoResult:
    """Wire and run the whole pipeline in data-flow order, deterministically from the
    config seed, and return everything it produced."""
    config = config or tiny_config()
    t0 = time.time()

    graph = build_service_graph(config)                      # static network
    injector = FaultInjector(graph, config)                  # telemetry + faults + truth
    engine = StructuralIntelligenceEngine(NetworkMap(graph), config)  # four-field detection
    formatter = DiagnosisFormatter(graph)                    # operator line + receipt
    harness = ScoringHarness(config)                         # score against truth
    model = ConsoleBuilder(graph).from_pipeline(injector, engine, formatter, harness)

    text_console = render_text(model)
    html_console = render_html(model)
    runtime = time.time() - t0

    return DemoResult(config=config, graph=graph, score_report=model.score_report,
                      console_model=model, text_console=text_console,
                      html_console=html_console, runtime_seconds=runtime)


def config_for_scale(scale: str, seed: Optional[int] = None) -> DemoConfig:
    """The configuration for a named scale: 'full' is the production picture, 'tiny'
    is the fast live run."""
    if scale == "full":
        return default_config(seed=seed) if seed is not None else default_config()
    return tiny_config(seed=seed) if seed is not None else tiny_config()


# ---------------------------------------------------------------------------
# The command-line entry point
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m si_core",
        description="Movistar Service Intelligence demo, powered by Structural "
                    "Intelligence. One command runs the whole pipeline on synthetic, "
                    "fault-injected data and prints the operator console.")
    p.add_argument("--scale", choices=["tiny", "full"], default="tiny",
                   help="tiny for a fast live run (default), full for the production "
                        "picture (thousands of homes; takes longer)")
    p.add_argument("--seed", type=int, default=None,
                   help="override the random seed (the run is deterministic from it)")
    p.add_argument("--out", default="movistar_si_console.html",
                   help="path to write the self-contained HTML console "
                        "(default movistar_si_console.html)")
    p.add_argument("--no-html", action="store_true",
                   help="do not write the HTML console")
    p.add_argument("--quiet", action="store_true",
                   help="print only the one-line summary, not the full text console")
    p.add_argument("--self-test", action="store_true",
                   help="run the internal self-test and exit non-zero on failure")
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = config_for_scale(args.scale, args.seed)

    if not args.quiet:
        print(f"Running the Movistar Service Intelligence demo at {args.scale} scale "
              f"(seed {config.seed}); the engine reads only four fields per entity.\n")

    result = run_demo(config)

    if args.quiet:
        print(result.summary())
    else:
        print(result.text_console)
        print("\n" + result.summary())

    if not args.no_html:
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(result.html_console)
            print(f"\nVisual console written to {args.out} (open it in a browser).")
        except OSError as exc:
            print(f"\nCould not write the HTML console to {args.out}: {exc}", file=sys.stderr)

    if args.self_test:
        ok = result.passed()
        print(f"\nSelf-test: {'PASSED' if ok else 'FAILED'}.")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
