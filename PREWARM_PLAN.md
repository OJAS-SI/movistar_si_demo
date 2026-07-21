# Seamless tiny ⇄ full toggle — plan & progress

## The problem, measured

| scale | homes | intervals | run_demo | fault panels |
|-------|-------|-----------|----------|--------------|
| tiny  | 48    | 60        | **0.2s** | 3            |
| full  | 2400  | 576       | **84s**  | 24           |

Three things make the toggle slow today, and only the third is obvious:

1. **Every toggle mints a new run.** `RunStore.create()` always allocates a fresh
   `run_id`, so switching full → tiny → full recomputes from scratch each time, even
   though a run is fully deterministic from `(scale, seed)`.
2. **The stream never reuses a finished run.** `stream.py` calls `replay(config)`
   unconditionally and recomputes all 576 intervals, even when the store already holds
   the completed `DemoResult`. Prewarming the batch run alone would not have helped.
3. **Nothing is computed until the operator asks for it**, so the 84s lands in the
   middle of the demo.

## The fix

- **Identity by `(scale, seed)`** — the same run is returned rather than recomputed.
- **Cache the replay frames on the run** — the second stream of a run is instant. Frames
  are cached as domain values, not as rendered JSON, so they still serialise into
  whichever language the socket asked for.
- **Prewarm both scales at startup**, in the background, so full is ready before anyone
  toggles. The server stays responsive while it happens.
- **Client keeps both consoles**, so toggling back does not even re-fetch.

## Progress

- [x] 1. `Run` carries cached frames; store indexes by `(scale, seed)`
- [x] 2. `create()` returns the existing run for a `(scale, seed)` it already has
- [x] 3. Stream serves from cached frames when present, fills the cache when not
- [x] 4. Prewarm both scales on startup (background, non-blocking)
- [x] 5. A `warm` flag on the API so the client can show readiness
- [x] 6. Not needed — a warm run returns `status: complete`, so the client's existing
       fast path takes it; no client change required
- [x] 7. Verify: cold vs warm toggle timings, and that a warm run is byte-identical


## Measured, after

| action | before | after |
|--------|--------|-------|
| select `full` (REST) | ~84 s | **1 ms** |
| stream 576 full frames | ~84 s | **0.04 s** |
| select `tiny` | 0.2 s | **1 ms** |
| server responds to health at startup | — | immediate, prewarm runs behind it |

`full` returns the **same `run_id`** every time — the run is reused, not recomputed.

Correctness: the prewarmed console is **byte-identical** to a plain `run_demo()` for the
same config (`served == expected` on the full 24-panel payload).

## Notes

- Prewarm is on by default; `SI_PREWARM=0` disables it for anyone iterating on `si_core`
  who does not want to pay 84s per reload.
- The full run is ready ~85s after server start. Toggling before then is not broken: the
  stream waits for the in-flight computation rather than starting a second one.
- `warm` is exposed on `GET /api/runs`, so the UI can show readiness if you want it.
