# EN/ES bilingual — progress tracker

Live file. Updated as each item lands. `[x]` means written **and** verified.

## Architecture (settled)

- `si_core` emits `Msg(key, params)` — never a finished sentence.
- `si_core/messages.py` holds the **canonical EN catalogue** and renders its own English,
  so the text console and HTML export keep working with no API.
- `si_api/i18n.py` holds **ES** and picks per request (`?lang=` → `Accept-Language` → EN).
- Frontend chrome is a plain dictionary in `frontend/src/lib/i18n.ts`.
- Numbers, ids, `action_code` are identical in both languages. Only prose changes.

---

## Backend

- [x] 1. Contracts: `Msg`, `ActionCode` (+ `action_code` on `Diagnosis`)
- [x] 2. `si_engine` emits codes and message keys
- [x] 3. `scoring` reads `ActionCode`, not prose — **box-swap landmine closed**
- [x] 4. EN catalogue is the single source of English (hand-written twins deleted)
- [x] 5. ES catalogue + language negotiation, full key parity
- [x] 6. `serializers` / `schemas` / routers thread the catalogue
- [x] 7. `console.py`: beats, panel titles, subtitle, config summary → `Msg`
- [x] 8. **Verify** full suite green after item 7 — all suites pass; ES beats/titles confirmed
- [x] 9. Scorecard text block bilingual, incl. the per-score traceability note

## Frontend

- [x] 10. `lib/i18n.ts` — language store, persistence, chrome dictionary
- [x] 11. API client + WebSocket carry `lang`
- [x] 12. `App` holds language; switching re-reads the console, never re-runs the engine
- [x] 13. Header EN/ES toggle
- [x] 14. Transport bar, ribbon legend, all tooltips
- [x] 15. `headline_short` / `health_band_short` rendered (the headline regression)
- [x] 16. `AlertQueue`
- [x] 17. `AnalystTab` labels, chips, measured grid, watching state
- [x] 18. `Receipt` incl. the recommended-action list
- [x] 19. `ManagementTab` — KPIs, table headers, abstention note
- [x] 20. `MapTab`
- [x] 21. `LiveDeck`
- [x] 22. `App` splashes (Starting / Failed)

## Close-out

- [x] 23. Typecheck clean · oxlint clean · build clean · all backend suites pass ·
       live EN/ES check: **0 non-prose differences** (every number, id and
       `action_code` byte-identical; only wording changes)

---

## Deliberately NOT done

- **Structural Health Index gauge.** The twin's `SHI 20 / 100` is a hand-authored
  keyframe series (`movistar_si_twin.html:428-437`), interpolated — the twin says
  "scripted replay". The engine has never measured an SHI. Restoring the gauge would
  mean inventing a number. Left as is at your instruction.


---

## Done

All 23 items complete. The console is bilingual end to end:

- Switching language re-reads the same run — it never re-runs the engine.
- `?lang=` wins, else `Accept-Language`, else English. Choice persisted to localStorage.
- Catalogue parity is asserted in `test_module9_messages.py`; a half-translated
  console fails CI rather than appearing on stage.
- Verified on a live run: EN vs ES differ **only** in prose.
