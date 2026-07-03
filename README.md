# Movistar Service Intelligence Demo

## Quick start

```
python run_demo.py                 # fast live run (tiny scale), prints the console
python run_demo.py --scale full    # the production picture (thousands of homes)
python run_demo.py --self-test     # run and exit non-zero if anything is off
python run_tests.py                # the full test suite (all modules)
```

The single command runs the entire pipeline on synthetic, fault-injected data (no
Telefonica data), prints the four-beat operator console and the scorecard, and writes
a self-contained HTML console you can open in a browser. The run is deterministic from
one seed.


A working prototype of **Structural Intelligence** for predictive fault
localization on an IPTV and fixed-broadband access network, demonstrated on a
100% synthetic, fault-injected model of a Telefonica-style Spanish network.

The demo proves one claim: *given only a stream of simple per-entity telemetry
from a service network, Structural Intelligence can detect a forming fault early,
name the exact element responsible, place it in its true layer, and recommend the
corrective action, including faults that carry no label and faults that survive a
set-top-box swap.*

This repository is built **module by module** on a frozen foundation. It is pure
Python standard library at its core, so it runs with no installation.

## Status

| Module | Name | State |
|-------|------|-------|
| 0 | Shared Foundations and Contracts | BUILT and frozen |
| 1 | Topology and identifier generator | BUILT and tested |
| 2 | Telemetry and baseline generator | BUILT and tested |
| 3 | Fault-injection engine and ground truth | BUILT and tested |
| 4 | Structural Intelligence engine | BUILT and tested |
| 5 | Diagnosis and certified-receipt formatter | BUILT and tested |
| 6 | Scoring harness | BUILT and tested |
| 7 | Visual narrative and operator console | BUILT and tested |
| 8 | Orchestrator and plug-and-play entry point | BUILT and tested |

## The architectural spine (read this first)

Three principles govern the whole codebase:

1. **The four-field boundary is structural.** The Structural Intelligence engine
   consumes only `CoreRecord`, which carries exactly four fields:
   `entity_src`, `entity_dst`, `timestamp`, `magnitude`. Everything else (firmware
   versions, multicast groups, optical power, channel names) travels on a separate
   `EnrichmentRecord` and is joined back to SI output only at the reporting stage,
   by the key `(entity_id, timestamp)`. `CoreRecord` is a frozen, slotted dataclass,
   so enrichment physically cannot ride along on the channel the SI engine reads.
   This is what proves SI needs only four fields while the demo still looks like
   real operator data.

2. **Ground truth exists by construction.** Because every fault is injected, every
   diagnosis is scored against a known answer. The ground-truth record is a
   first-class output, not an afterthought.

3. **The honesty instruments are built in from the first module.** Decoys (benign
   anomalies that must not fire) and long healthy stretches live in the fault
   schedule, the scoring harness measures false positives as a primary metric, and
   every diagnosis carries its evidence (the certified-decision receipt).

## Module 0 - what is in this release

`si_demo/core/` is the frozen vocabulary every later module imports:

- `types.py` - the data contracts: `CoreRecord` (the four-field boundary),
  `EnrichmentRecord`, `Diagnosis` / `Evidence` / `Provenance` /
  `PredictedTrajectory`, `GroundTruthLabel`, `Score`, and the enumerations
  `Layer`, `EntityType`, `Shape`, `UseCase`, `RampProfile` with `SHAPE_TO_LAYER`.
- `config.py` - `DemoConfig` and the canonical six-region Spanish configuration
  (`default_config`), grounded in Telefonica's public footprint, plus `tiny_config`
  for fast tests.
- `rng.py` - `SeededRandom`, deterministic seeding with independent named child
  streams, so a run is fully reproducible and modules never perturb each other.
- `contracts.py` - the boundary guards (`assert_four_field_boundary`,
  `assert_core_stream_clean`) and the frozen-contract version marker.

Import everything from the single surface `si_demo.core`.

## Module 1 - what is in this release

`si_demo/topology.py` builds the static service graph once per run:

- `build_service_graph(config)` constructs the Telefonica-style GPON/FTTH hierarchy
  (STB to ONT to OLT to aggregation switch to BNG to core route to CDN edge to
  content) across the six Spanish regions, with authentic MIGA-style identifiers
  (7-digit central-office codes like `2807001`, OLTs like `OLT-2807001-03`, homes
  like `STB-2807001-03-042`, multicast groups in the `239/8` IPTV range, CDN edges
  named by city such as `CDN-MAD-2`).
- It returns a `ServiceGraph` carrying the nodes, the access-tree edges, and the
  per-home `Membership` index, plus the reverse groupings `stbs_by_olt`,
  `stbs_by_route`, and `stbs_by_content`. These three groupings are what make the
  four fault shapes computable: a cluster behind one OLT (access), a path across a
  core route (core), and a source impairing otherwise-unrelated homes (content).
- It carries only static identity; it emits no magnitudes, preserving the
  four-field boundary. The central office is an attribute, not a node.

## Module 2 - what is in this release

`si_demo/telemetry.py` generates the continuous, regularly-sampled stream over the
graph for a HEALTHY network (Module 3 will perturb it to inject faults):

- `TelemetryGenerator(graph, config)` produces two streams per interval. The
  **core stream** is what the SI engine reads: each home emits three independent
  subsystem edges per interval, `(STB -> OLT)` access impairment, `(STB -> route)`
  transport impairment, and `(STB -> content)` content impairment, each a
  non-negative severity on a low per-home baseline with noise and prime-time
  seasonality. Because the three are independent, a fault in one subsystem does not
  pollute the others, which is what lets the engine attribute cleanly.
- The **enrichment stream** populates the full per-layer data-dictionary fields for
  every entity every interval (`freeze_duration`, `port_utilization`,
  `transport_load`, `segment_failures`, `wifi_snr`, and so on), joined to the core
  stream only by `(entity_id, timestamp)`. The SI engine never sees it.
- `interval(t)` is a deterministic pure function of `t`; `stream()` yields the whole
  run. On a healthy network every magnitude stays below a healthy ceiling, so the
  engine raises nothing. `IntervalTelemetry.core_index` lets Module 3 find and
  perturb a specific home/subsystem edge.

## Module 3 - what is in this release

`si_demo/fault_injection.py` perturbs the healthy stream to inject faults, and
records the answer key by construction:

- `FaultInjector(graph, config)` wraps the telemetry generator. `interval(t)`
  returns the FAULTED telemetry for interval `t`; `ground_truth_labels()`,
  `real_faults()`, and `decoys()` return the recorded answer key.
- Each use case is mapped onto exactly the subsystem edge whose shape it should
  produce: **UC1** raises the access edge of every home behind one OLT (a cluster,
  access layer); **UC2** raises the access edge of one isolated home while its peers
  stay flat (a single, home layer), with a tipping point recorded; **UC3** raises a
  small access segment with NO error code and a box-swap event the fault
  deliberately survives (a cluster, access layer, proven not to be the box).
- The **honesty instruments** are built in: decoys (a prime-time load spike, a
  one-off home glitch, an isolated reboot) are short transients recorded as benign,
  and the long healthy stretches between events let the demo measure the
  false-positive rate. Real faults persist and exceed the healthy ceiling; decoys
  only tempt. That persistence gap is the discriminator the engine will use.
- The four-field boundary holds: only the magnitude changes in the core stream;
  enrichment is perturbed in step (freeze duration, port utilization, error code)
  solely for the operator report.

## Module 4 - what is in this release

`si_demo/si_engine.py` is the intellectual core. It consumes ONLY the four-field
core stream and learns its baselines from it:

- `StructuralIntelligenceEngine(network_map, config)` processes the stream interval
  by interval; `observe_and_diagnose(t, core_records)` returns the findings (an empty
  list means all clear). The `NetworkMap` is the operator's known wiring (node layers
  and the home groupings behind each access node, route, and content), used only to
  NAME a layer, never as a fault signal.
- It learns a per-edge baseline online (frozen while an edge is anomalous so a fault
  cannot poison its own reference), measures each edge's departure, and applies a
  persistence (dwell) gate so brief decoys never fire. It then reads the SHAPE of a
  convergence (cluster, single, path, source), names the element and its true layer,
  projects the forming shape forward, and attaches an explainable receipt.
- The competence boundary is built in: when a convergence is too weak or ambiguous,
  the engine ABSTAINS and defers to a human rather than guessing. On the demo data it
  detects all three faults, attributes each correctly, fires on no decoy or healthy
  interval, and abstains only at a genuine ramp-edge ambiguity.
- The boundary is enforced at the entry: `observe_and_diagnose` runs the core stream
  through the four-field guard, so enrichment can never reach the engine.

## Module 5 - what is in this release

`si_demo/diagnosis.py` turns the engine's structural verdict into the operator-facing
artifact:

- `DiagnosisFormatter(graph).format(diagnosis, interval_telemetry)` joins the
  diagnosis to the enrichment for its named entity by `(entity_id, timestamp)` and
  produces a `DiagnosisReport`: a one-line recommendation in the form Nodofact
  specified (the named element, its region and central office, the home count, the
  symptom and time window, the signature, and the action), a Structural Health Index
  band, and a certified-decision receipt beneath it (claim, evidence, an independent
  cross-check, provenance, and confidence). `report.render()` prints the block.
- Enrichment enters here and only here, to colour the line (access-node port
  utilization, a home's Wi-Fi SNR, a content source's segment failures), clearly as
  corroborating context, never as the basis of detection. The headline count is
  exactly the engine's sustained signature, so the line and the receipt agree.
- An abstention renders as a deferral to a human; all-clear renders cleanly. The
  whole artifact stays in the external register: the three coined handles and plain
  telecom language, with none of the internal vocabulary, enforced by a test.

## Module 6 - what is in this release

`si_demo/scoring.py` runs the engine over the faulted stream and scores it against
the answer key, reporting measured values with no pre-committed thresholds:

- `ScoringHarness(config).evaluate(injector, engine)` returns a `ScoreReport`: one
  `Score` per use case plus the global false-positive accounting. `report.render()`
  prints the scorecard.
- Per use case it measures detection lead time (intervals before the fault would
  surface, its plateau or recorded tipping point, converted to minutes), localization
  accuracy (did the settled verdict name the true element), layer attribution (the
  true layer), box-swap discrimination for the invisible fault (attributed off the
  home with a network-side action, so the box swap is avoided), and action
  correctness judged by category against the true layer. Globally it measures the
  false-positive rate across every interval where no real fault is active, the decoys
  and the long healthy stretches, and counts how many decoys fired.
- The settled verdict is the element the engine named most often across the fault's
  life, so a brief ramp-edge read does not stand in for the engine's conclusion.
  Every number is traceable to the ground truth, so the scorecard can be checked by
  hand. On the demo data: all three faults detected and attributed, the box swap
  avoided, and zero false positives.

## Module 7 - what is in this release

`si_demo/console.py` is the face of the demo. It reads ONLY from the verdicts, the
diagnoses, the receipts, and the scorecard, never from the four-field stream; the
static graph is used only to draw the picture.

- `ConsoleBuilder(graph).from_pipeline(injector, engine, formatter, harness)` runs
  the pipeline and assembles a `ConsoleModel`; `build(findings, score_report,
  abstention)` is the pure assembly from verdicts alone.
- For each use case it lays out the four-beat narrative (Stream, Form, Predict,
  Prescribe), the operator recommendation and its certified-decision receipt, a small
  schematic of the forming shape lit up on the layered graph, and the per-use-case
  score. The verdict shown is the earliest one where the engine's projection is
  rising, so the story catches the fault while it is still forming.
- It then shows the honest instruments plainly: the competence boundary (an
  abstention) and the decoys that did not fire, with the measured false-positive rate.
  A scorecard panel closes it.
- `render_text(model)` prints a terminal console; `render_html(model)` produces a
  self-contained visual console (no external assets) that opens in any browser.

## Module 8 - what is in this release

`si_demo/orchestrator.py` wires the whole pipeline in data-flow order behind a single
call, deterministic from one seed:

- `run_demo(config)` builds the graph, injects faults, runs the engine on the
  four-field stream, formats the diagnoses, scores them, builds the console, and
  renders it, returning a `DemoResult` with the text console, the HTML console, the
  scorecard, and a `passed()` self-test (all faults detected and attributed, the box
  swap avoided, no false positives).
- The command-line entry point runs the whole demo: `python -m si_demo` (or
  `python run_demo.py`) for a fast live run at tiny scale, `--scale full` for the
  production picture, `--seed N` to choose the seed, `--out PATH` for the HTML
  console, `--self-test` to exit non-zero if anything is off, and `--quiet` for the
  one-line summary. The run is robust across seeds, not just the default.

## Running the tests

No dependencies required. From anywhere:

```
python run_tests.py
```

or individually:

```
python tests/test_module0_foundations.py     # Module 0 standalone test
python tests/test_integration.py              # growing integration test
```

Each module ships with a standalone test (exercising it in isolation) and
contributes to the integration test (confirming the assembled pipeline so far),
so functionality is verified both standalone and integrated at every step.
