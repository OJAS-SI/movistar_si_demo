# Continue from here — Movistar SI demo session handoff

_Last worked: 2026-07-15._

> **Newer session available.** See **`SESSION-2026-07-21.md`** — bilingual EN/ES, the
> tiny⇄full prewarm, the alert-selection bug, the management-view fixes and the layout
> work. Where the two disagree, the newer file wins. Companion trackers:
> `I18N_PROGRESS.md`, `PREWARM_PLAN.md`.

This file is a context dump of a full working session so you (or Claude) can resume
without re-deriving anything. Read the **Open threads** section first.

---

## What this project is

Movistar **Structural Intelligence** demo — predictive fault localization on a synthetic,
fault-injected Telefonica-style Spanish access network. Three layers:

- `backend/si_core/` — the domain engine. **Pure Python stdlib**, frozen four-field
  contract (`entity_src, entity_dst, timestamp, magnitude`). Knows nothing about HTTP.
- `backend/si_api/` — FastAPI transport: runs, console, scorecard, topology, WebSocket
  replay stream. The only layer allowed to import `si_core`.
- `frontend/` — React 19 / Vite 8 operator console (Analyst / Management / Map tabs).

Two scales via the top-right toggle: **Tiny** (48 homes, 60 intervals, sub-second) and
**Full** (2401 homes, 6 regions, 576 intervals, ~80s to compute).

---

## What was done this session (chronological)

1. **End-to-end test pass.** 130 backend tests pass (`python run_tests.py`), CLI self-test
   passes, API + WebSocket + frontend build all verified. Found the committed
   `frontend/dist/` bundle was **stale** — rebuilt it.

2. **Ran the app for manual testing.** uvicorn on `:8000`, Vite on `:5173`.
   Fixed: Vite was binding **IPv6-only** (`[::1]`), so `127.0.0.1:5173` was refused —
   now launched with `--host 127.0.0.1`.

3. **UI: reordered the named-verdict layout** (`frontend/src/components/analyst/AnalystTab.tsx`).
   The three panels — *The shape on the graph*, *The call*, *Measured against ground truth* —
   now render **above** the four Stream/Form/Predict/Prescribe beats.

4. **UI: replay no longer auto-plays** (`frontend/src/hooks/useReplay.ts`). Removed the
   `setPlaying(true)` in the stream's `onEnd`. It loads paused at interval 0; press ▶.

5. **Explained Tiny vs Full.** Toggle → `config_for_scale()` → `tiny_config()` /
   `default_config()` in `backend/si_core/contracts/config.py`. Same engine, same seed;
   only scale + run length differ.

6. **Full-scale fault set expanded (the big one).** Previously **3 real faults + 3 decoys**
   for both scales. Now **Full injects ~24 realistic faults** across **all 6 regions** and
   **all 4 layers** (access clusters, isolated homes, core-transport paths, content
   sources), on top of the 3 scripted anchors. **Tiny is unchanged (still 3).**
   - New `UseCase.UC4_CORE_PATH` / `UC5_CONTENT_SOURCE` in `contracts/types.py`.
   - New `_build_extra_faults()` + `_is_full_scale()` in `fault_injection.py`, wired into
     `build_fault_schedule()` (full only).
   - `console.py`: added titles for UC4/UC5; fixed score→fault join (was matching by
     use-case, which collides when many faults share a category — now paired by position).
   - Verified: **24/24 detected, 100% localization/layer, 0% false positives, 0/3 decoys
     fired, deterministic.**

7. **Progressive streaming load (the other big one).** The Full toggle used to block the
   UI for ~80s. Fixed so the **WebSocket stream is the single computation**:
   - Run created **lazily** (`execute=false`); the stream computes it once and stores the
     finished console when it ends (no double compute under the GIL).
   - `orchestrator.assemble_result()` + `ConsoleBuilder.from_collected()` build the console
     from already-collected diagnoses — no recompute.
   - Frontend renders immediately; new `LiveDeck` (`frontend/src/components/LiveDeck.tsx`)
     shows faults **as they're detected**, then swaps to the full analyst view when done.
   - Tiny keeps its instant eager path.
   - Verified via headless Chrome: deck live at ~4s, 9 faults by ~26s, full view on
     completion.

8. **Git + sharing.** Committed everything, created a **private personal repo**, opened a
   PR, notified Gabriel, and also pushed the branch to the OJAS-SI org repo. See **Git
   state** below.

---

## Files touched (all in commit `603b874`)

**Backend**
- `si_core/contracts/types.py` — UC4/UC5 use-cases.
- `si_core/fault_injection.py` — `_build_extra_faults`, `_is_full_scale`, wiring.
- `si_core/console.py` — `from_collected`, UC4/UC5 titles, score-join fix.
- `si_core/orchestrator.py` — `assemble_result`, `run_demo` refactor.
- `si_core/si_engine.py` — whitespace only (pre-existing working-tree edit).
- `si_api/services/replay.py` — generator returns collected pipeline; `Done` sentinel.
- `si_api/routers/stream.py` — assemble + store result at stream end (`_finalize`).
- `si_api/services/run_store.py` — `execute` flag, `complete_with()`.
- `si_api/routers/runs.py` — `execute` query param.
- `tests/test_module0_foundations.py` — enum-membership assertion updated.

**Frontend**
- `hooks/useDemoRun.ts` — non-blocking Full, `computing` flag, poll for console.
- `hooks/useReplay.ts` — no auto-play.
- `lib/alerts.ts` — `liveFaults()` + `LiveFault`.
- `components/LiveDeck.tsx` — NEW, the live streaming deck.
- `components/analyst/AnalystTab.tsx` — panel reorder.
- `components/Header.tsx` — scale toggle always enabled.
- `App.tsx` — render LiveDeck while computing.
- `styles.css` — `.livedeck` / `.live-*` styles.
- (The whole `si_api/` and `frontend/` trees were previously untracked; this commit adds them.)

---

## Git state

- **Local branch:** `restructure-layers` @ `603b874` (authored `sumankalyan70 <sumankalyan70@gmail.com>`).
- **Remotes:**
  - `origin` → `https://github.com/OJAS-SI/movistar_si_demo.git` (OJAS org).
  - `personal` → `https://github.com/sumankalyan70/movistar_si_demo.git` (private, created this session).
  - NOTE: local `main` and `restructure-layers` now **track `personal`** (not origin), so a
    plain `git push` goes to the personal repo, not OJAS.
- **Personal repo (private):** `main` + `restructure-layers` pushed. **PR #1** open
  (`restructure-layers → main`): https://github.com/sumankalyan70/movistar_si_demo/pull/1
  - Gabriel Trautmann (`gtr-trautmann`) invited as collaborator (**invite pending**) and
    @mentioned in the PR.
- **OJAS-SI repo:** `restructure-layers` branch pushed; **`main` untouched**; no PR opened.
  - Open one if wanted: https://github.com/OJAS-SI/movistar_si_demo/pull/new/restructure-layers

---

## How to resume / run it

```bash
cd "/Users/sumankalyan/PycharmProjects/Movistar Demo"

# backend (API on :8000)
pip install -r backend/requirements.txt        # fastapi, uvicorn, pydantic
python -m uvicorn si_api.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload

# frontend (UI on :5173) — MUST bind IPv4 or the browser gets connection-refused
cd frontend && npm install && npm run dev -- --host 127.0.0.1
# open http://127.0.0.1:5173

# CLI / tests
python run_demo.py --scale full --self-test     # ~80s, expects 24/24
python run_tests.py                             # 130 tests
```

The dev servers from this session (uvicorn :8000, Vite :5173) were left running but will
likely be gone when you return — just restart with the commands above.

---

## Open threads / next steps (in rough priority)

1. **UI for many concurrent faults.** The Analyst alert queue, the Map pins, and the
   "following"/pinned-alert behavior were designed around ~3 alerts. With ~24 faults on
   Full they work but were not reviewed for readability/scale. **This is the natural next
   piece of work.**

2. **Progressive full view.** Faults now stream in live, but the *full* analyst view
   (settled receipts + scorecard measured against ground truth) still waits for the ~80s
   run to finish before it swaps in. Optional next step: have the LiveDeck carry the
   settled receipts / scorecard progressively too (would need the stream to emit
   console/scorecard incrementally rather than only at the end).

3. **Request Gabriel's review** once he accepts the collaborator invite:
   ```bash
   gh pr edit 1 --repo sumankalyan70/movistar_si_demo --add-reviewer gtr-trautmann
   ```
   (Couldn't attach it yet — GitHub blocks review requests to pending-invite collaborators.)

4. **OJAS-SI PR** — not opened per your instruction; open it (and pick reviewers) if/when
   you want it reviewed there.

5. **Optional:** run caching/dedup by `(scale, seed)` so re-toggling doesn't recompute;
   the eager-batch-plus-stream double compute on Tiny is negligible but could be unified.

6. **Housekeeping:** `frontend/dist/` is git-ignored; rebuild before any deploy that serves
   the built bundle from FastAPI (`cd frontend && npm run build`).

---

## Design invariants to respect (don't break these)

- **Four-field boundary:** the SI engine reads only `CoreRecord` (4 fields). Enrichment
  never crosses into `si_engine`. `si_core` stays pure stdlib (no deps ever).
- **Ground truth by construction:** every injected fault is scored against a known answer.
- **Honesty instruments:** decoys must NOT fire; false-positive rate is a primary metric.
- **Tiny is the fast sanity path** — keep it unchanged / instant.
- Runs are **deterministic** from `(scale, seed)`.